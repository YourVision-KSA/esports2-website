"""Regression tests for the security assessment of 2026-11-19 (core app):
YV-07 network keys, YV-37 admin history purge, YV-38 staff login, YV-40 secret headers,
and the critic's /beacon/3d limit. Several started as the reviewers' PoC tests."""

import re

import pytest
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import override_settings
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

from core.models import SiteConfig, StaffLoginFailure, TierStat
from core.security import network_key, secret_matches
from core.staff_login import INVALID_LOGIN, THROTTLED

pytestmark = pytest.mark.django_db


# ------------------------------------------------------------------ YV-07 network key


@pytest.mark.parametrize(
    "ip, expected",
    [
        ("203.0.113.7", "203.0.113.7/32"),
        ("2001:db8:1:2::9", "2001:db8:1:2::/64"),
        ("2001:db8:1:2:ffff:ffff:ffff:ffff", "2001:db8:1:2::/64"),
        ("::ffff:203.0.113.7", "203.0.113.7/32"),  # IPv4-mapped = that IPv4 address
        ("64:ff9b::cb00:7107", "64:ff9b::cb00:7107/128"),  # NAT64: one IPv4 inside
        ("not-an-ip", "not-an-ip"),
        ("", ""),
    ],
)
def test_network_key_groups_ipv6_by_64(ip, expected):
    assert network_key(ip) == expected


# --------------------------------------------------------------- YV-40 secret headers


@override_settings(CF_ORIGIN_TOKEN="abc")
@pytest.mark.parametrize("sent", ["ÿ", "é", "abcé"])
def test_non_ascii_origin_token_is_403_not_500(client, sent):
    client.raise_request_exception = False
    assert client.get("/", HTTP_X_ORIGIN_TOKEN=sent).status_code == 403


@override_settings(INTERNAL_TOKEN="abc")
@pytest.mark.parametrize("sent", ["é", "ÿ"])
def test_non_ascii_internal_token_is_403_not_500(client, sent):
    client.raise_request_exception = False
    assert client.post("/internal/outbox/", HTTP_X_INTERNAL_TOKEN=sent).status_code == 403


def test_secret_matches_never_raises():
    assert secret_matches("abc", "abc")
    assert not secret_matches("一", "abc")
    assert not secret_matches("\udcff", "abc")  # lone surrogate
    assert not secret_matches("", "")  # an unset secret never matches


# ------------------------------------------------------------- YV-37 admin history


def test_purge_pii_anonymizes_names_in_the_admin_history(client):
    """Reviewer PoC test_verify_logentry: a VIP added through the admin left their name
    in django_admin_log.object_repr after the purge."""
    admin = get_user_model().objects.create_superuser("root", "r@example.invalid", "x" * 16)
    client.force_login(admin)
    response = client.post(
        "/staff/invitations/invitation/add/",
        {
            "guest_name": "VIP Secret Name",
            "organization": "Org",
            "contact_email": "",
            "contact_phone": "",
        },
    )
    assert response.status_code == 302
    assert LogEntry.objects.filter(object_repr__contains="VIP Secret Name").exists()

    cfg = SiteConfig.get_solo()
    cfg.archived = True
    cfg.save()
    call_command("purge_pii", "--yes")

    assert not LogEntry.objects.filter(object_repr__contains="VIP Secret Name").exists()
    entry = LogEntry.objects.get()
    assert entry.object_repr == "purged" and entry.user == admin  # who/when is kept


# ------------------------------------------------------------------ YV-38 staff login

PASSWORD = "Correct-Horse-Battery-9"


@pytest.fixture
def staff_user(django_user_model):
    user = django_user_model.objects.create_user(
        "referee", password=PASSWORD, is_staff=True, is_superuser=True
    )
    device = TOTPDevice.objects.create(user=user, name="phone", confirmed=True)
    return user, device


def _code(device):
    return str(totp(device.bin_key, step=device.step, t0=device.t0, digits=device.digits)).zfill(
        device.digits
    )


@pytest.fixture
def otp_login_page(monkeypatch):
    """Production renders django-otp's admin login template (OTPAdminSite); use it here
    too, because that template is what showed the device list after a right password."""
    from django.contrib import admin

    monkeypatch.setattr(admin.site, "login_template", "otp/admin111/login.html")


def _login(client, username, password, code="", ip="198.51.100.10"):
    return client.post(
        "/staff/login/?next=/staff/",
        {"username": username, "password": password, "otp_token": code, "next": "/staff/"},
        REMOTE_ADDR=ip,
    )


def _page(response):
    """The page without its per-request CSRF token."""
    return re.sub(r'name="csrfmiddlewaretoken" value="[^"]+"', "", response.content.decode())


@override_settings(REQUIRE_2FA=True)
def test_staff_login_does_not_reveal_a_correct_password(client, staff_user, otp_login_page):
    wrong_password = _login(client, "referee", "wrong-password")
    right_password_no_code = _login(client, "referee", PASSWORD)
    right_password_bad_code = _login(client, "referee", PASSWORD, code="000000")
    for response in (wrong_password, right_password_no_code, right_password_bad_code):
        assert response.status_code == 200
        assert INVALID_LOGIN in response.content.decode()
        assert "OTP Device" not in response.content.decode()
    assert _page(right_password_no_code) == _page(wrong_password)
    assert _page(right_password_bad_code) == _page(wrong_password)


@override_settings(REQUIRE_2FA=True)
def test_staff_login_succeeds_in_one_step_with_password_and_code(client, staff_user):
    user, device = staff_user
    response = _login(client, "referee", PASSWORD, code=_code(device))
    assert response.status_code == 302 and response["Location"] == "/staff/"
    assert client.session["_auth_user_id"] == str(user.pk)
    assert client.session["otp_device_id"] == device.persistent_id  # session is verified
    assert not StaffLoginFailure.objects.exists()


@override_settings(REQUIRE_2FA=True, STAFF_LOGIN_FAILURES_PER_ACCOUNT=3)
def test_staff_login_is_throttled_per_account(client, staff_user):
    _, device = staff_user
    for i in range(3):  # spread over many networks: still one account
        _login(client, "Referee", f"guess-{i}", ip=f"203.0.113.{i}")
    # Now even the right password and code are not checked: throttled.
    response = _login(client, "referee", PASSWORD, code=_code(device), ip="198.51.100.99")
    assert response.status_code == 200
    assert THROTTLED in response.content.decode()
    assert "_auth_user_id" not in client.session
    stored = StaffLoginFailure.objects.values_list("username_hash", "network_hash")
    assert all("referee" not in u.lower() and "203.0.113" not in n for u, n in stored)


@override_settings(REQUIRE_2FA=True, STAFF_LOGIN_FAILURES_PER_NETWORK=3)
def test_staff_login_is_throttled_per_network(client, staff_user):
    _, device = staff_user
    for i in range(3):  # credential stuffing: many usernames, one IPv6 /64
        _login(client, f"user{i}", "pw", ip=f"2001:db8:1:2::{i + 1}")
    blocked = _login(client, "referee", PASSWORD, code=_code(device), ip="2001:db8:1:2::99")
    assert THROTTLED in blocked.content.decode()
    other_network = _login(client, "referee", PASSWORD, code=_code(device), ip="2001:db8:9::1")
    assert other_network.status_code == 302


@override_settings(REQUIRE_2FA=False)
def test_password_only_login_still_works_where_2fa_is_off(client, staff_user):
    assert _login(client, "referee", PASSWORD).status_code == 302


# ------------------------------------------------------------- critic: /beacon/3d


def _beacon(client, ip):
    return client.post(
        "/beacon/3d",
        "o=mid&d=mobile",
        content_type="application/x-www-form-urlencoded",
        REMOTE_ADDR=ip,
    )


@override_settings(BEACON_PER_NETWORK_10MIN=3)
def test_beacon_is_limited_per_network_without_cloudflare(client):
    for i in range(3):
        assert _beacon(client, f"2001:db8:5:6::{i + 1}").status_code == 204
    # same IPv6 /64, new address: over the limit, not counted
    assert _beacon(client, "2001:db8:5:6::abcd").status_code == 429
    assert TierStat.objects.get().count == 3
    # another network still counts
    assert _beacon(client, "203.0.113.50").status_code == 204
    assert TierStat.objects.get().count == 4
