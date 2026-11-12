"""Registration abuse controls (audit 2026-11-13, finding 1 — High): server-side Turnstile,
application-side limits per client / device / phone, and the staff tools for the day a
scripted wave or a squatted phone number happens anyway (bulk removal with correct
waitlist promotion, phone release) — all audited."""

import pytest
from django.contrib.auth.models import User
from django.test import override_settings

from conftest import make_player
from core.content import CONTENT
from core.models import AuditLog
from registration import services
from registration.models import Player, Registration, RegistrationAttempt

pytestmark = pytest.mark.django_db

IP = "198.51.100.23"
UA = "Mozilla/5.0 (test)"


def post(client, game, phone="0551234567", ip=IP, ua=UA, meta=None):
    data = {
        "full_name": "لاعب",
        "phone": phone,
        "email": "",
        "game_player_id": f"tag-{phone}",
        "consent": "on",
        "cf-turnstile-response": "token",
    }
    return client.post(
        f"/register/{game.slug}/", data, REMOTE_ADDR=ip, HTTP_USER_AGENT=ua, **(meta or {})
    )


def phone(i: int) -> str:
    return f"055{i:07d}"


# ------------------------------------------------------------------ Turnstile


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SITE_KEY="site-key")
@pytest.mark.parametrize("verdict", [False, None])  # failed, and Turnstile unreachable
def test_registration_rejected_without_a_passed_bot_check(
    client, phase_registration, game, monkeypatch, verdict
):
    monkeypatch.setattr("core.turnstile.verify", lambda token, ip="": verdict)
    response = post(client, game)
    assert response.status_code == 400
    assert CONTENT["ERR_RETRY"] in response.content.decode()
    assert not Registration.objects.exists()  # no seat for an unchecked request
    assert RegistrationAttempt.objects.get().outcome == "turnstile"


@override_settings(TURNSTILE_ENABLED=True, TURNSTILE_SITE_KEY="site-key")
def test_registration_with_passed_bot_check_goes_through(
    client, phase_registration, game, monkeypatch
):
    seen = {}

    def verify(token, ip=""):
        seen["token"], seen["ip"] = token, ip
        return True

    monkeypatch.setattr("core.turnstile.verify", verify)
    assert 'data-sitekey="site-key"' in client.get(f"/register/{game.slug}/").content.decode()
    response = post(client, game)
    assert response.status_code == 302
    assert seen == {"token": "token", "ip": IP}
    attempt = RegistrationAttempt.objects.get()
    assert attempt.outcome == "registered" and attempt.registration is not None


# ---------------------------------------------------------- application limits


@override_settings(REG_IP_ATTEMPTS_PER_10MIN=3)
def test_attempts_per_client_are_limited(client, phase_registration, game):
    for _ in range(3):
        post(client, game, phone="not-a-phone")  # invalid attempts count too
    response = post(client, game, phone=phone(1))
    assert response.status_code == 429
    assert CONTENT["REG_RATE_LIMITED"] in response.content.decode()
    assert not Registration.objects.exists()
    # a different client is not affected
    assert post(client, game, phone=phone(2), ip="203.0.113.77").status_code == 302


@override_settings(REG_IP_ATTEMPTS_PER_10MIN=2, CF_ORIGIN_TOKEN="shield")
def test_limit_follows_the_trusted_client_ip_behind_cloudflare(client, phase_registration, game):
    """Behind the origin shield every request arrives from a Cloudflare address; the
    limit must key on CF-Connecting-IP (core.security.client_ip), not the socket."""

    def via_cloudflare(real_ip):
        return {"HTTP_X_ORIGIN_TOKEN": "shield", "HTTP_CF_CONNECTING_IP": real_ip}

    for _ in range(2):
        post(client, game, phone="bad", ip="10.0.0.1", meta=via_cloudflare("203.0.113.5"))
    # same real client through another Cloudflare node → still limited
    limited = post(client, game, phone=phone(3), ip="10.0.0.2", meta=via_cloudflare("203.0.113.5"))
    assert limited.status_code == 429
    # another real client through the same Cloudflare node → not limited
    other = post(client, game, phone=phone(4), ip="10.0.0.1", meta=via_cloudflare("203.0.113.6"))
    assert other.status_code == 302


@override_settings(REG_DEVICE_REGISTRATIONS_PER_DAY=2)
def test_registrations_per_device_are_capped(client, phase_registration, game):
    assert post(client, game, phone=phone(1)).status_code == 302
    assert post(client, game, phone=phone(2)).status_code == 302
    assert post(client, game, phone=phone(3)).status_code == 429
    assert Registration.objects.count() == 2
    # same network, another device (user agent) may still register
    assert post(client, game, phone=phone(4), ua="Other/1.0").status_code == 302


@override_settings(REG_IP_REGISTRATIONS_PER_DAY=2, REG_DEVICE_REGISTRATIONS_PER_DAY=10)
def test_registrations_per_network_are_capped(client, phase_registration, game):
    for i in range(2):
        assert post(client, game, phone=phone(i), ua=f"UA{i}").status_code == 302
    assert post(client, game, phone=phone(9), ua="UA9").status_code == 429


@override_settings(REG_PHONE_ATTEMPTS_PER_DAY=2)
def test_attempts_per_phone_number_are_limited(client, phase_registration, game):
    """Slows down probing which numbers are registered, from any number of clients."""
    make_player(77, phone="+966551112233")
    for i in range(2):
        post(client, game, phone="0551112233", ip=f"203.0.113.{i}")
    response = post(client, game, phone="0551112233", ip="203.0.113.99")
    assert response.status_code == 429


def test_attempt_rows_hold_hashes_only(client, phase_registration, game):
    post(client, game, phone="0551234567")
    attempt = RegistrationAttempt.objects.get()
    stored = " ".join([attempt.ip_hash, attempt.ua_hash, attempt.phone_hash])
    for raw in (IP, UA, "0551234567", "+966551234567"):
        assert raw not in stored
    assert len(attempt.ip_hash) == 64 and len(attempt.phone_hash) == 64


# ------------------------------------------------------------- operator tools


@pytest.fixture
def admin_client(client, django_user_model):
    django_user_model.objects.create_superuser("boss", password="x")
    client.login(username="boss", password="x")
    return client


def _seed_wave(game):
    """13 real + 3 fake confirmed; waitlist: fake, real, fake, real, real."""
    regs = {}
    for i in range(16):
        kind = "fake" if i < 3 else "real"
        regs[f"{kind}-c{i}"] = Registration.objects.create(
            player=make_player(100 + i),
            game=game,
            status=Registration.Status.CONFIRMED,
            game_player_id=f"{kind}-c{i}",
        )
    for pos, kind in enumerate(["fake", "real", "fake", "real", "real"], start=1):
        regs[f"{kind}-w{pos}"] = Registration.objects.create(
            player=make_player(200 + pos),
            game=game,
            status=Registration.Status.WAITLISTED,
            waitlist_position=pos,
            game_player_id=f"{kind}-w{pos}",
        )
    return regs


def test_bulk_removal_promotes_only_real_players_in_fifo_order(admin_client, game):
    regs = _seed_wave(game)
    fakes = [r.pk for key, r in regs.items() if key.startswith("fake")]

    response = admin_client.post(
        "/staff/registration/registration/",
        {
            "action": "remove_registration",
            "_selected_action": fakes,
            "confirm": "yes",
            "reason": "scripted wave 2026-11-16 10:02",
        },
    )
    assert response.status_code == 302

    statuses = {r.game_player_id: r.status for r in Registration.objects.all()}
    assert all(statuses[f"fake-{k.split('-')[1]}"] == "removed" for k in regs if "fake" in k)
    # 3 seats freed → the 3 real waitlisted players, in their order; never a fake
    assert statuses["real-w2"] == statuses["real-w4"] == statuses["real-w5"] == "confirmed"
    assert game.registrations.filter(status="confirmed").count() == 16
    assert not game.registrations.filter(status="waitlisted").exists()
    promoted = AuditLog.objects.filter(action="registration.promote")
    assert {int(p.object_id) for p in promoted} == {
        regs["real-w2"].pk,
        regs["real-w4"].pk,
        regs["real-w5"].pk,
    }
    removals = AuditLog.objects.filter(action="registration.remove")
    assert removals.count() == len(fakes)
    assert all(r.actor.username == "boss" for r in removals)
    assert all(r.after["reason"] == "scripted wave 2026-11-16 10:02" for r in removals)


def test_bulk_removal_asks_for_confirmation_and_a_reason(admin_client, game):
    regs = _seed_wave(game)
    body = admin_client.post(
        "/staff/registration/registration/",
        {"action": "remove_registration", "_selected_action": [regs["fake-c0"].pk]},
    ).content.decode()
    assert "Reason" in body
    assert Registration.objects.get(pk=regs["fake-c0"].pk).status == "confirmed"


def test_removal_service_keeps_waitlist_dense(game):
    regs = _seed_wave(game)
    services.remove_registrations([regs["fake-w1"].pk], actor=None, reason="fake")
    positions = list(
        game.registrations.filter(status="waitlisted")
        .order_by("waitlist_position")
        .values_list("game_player_id", "waitlist_position")
    )
    assert positions == [("real-w2", 1), ("fake-w3", 2), ("real-w4", 3), ("real-w5", 4)]


def test_released_phone_can_be_registered_by_its_owner(
    client, admin_client, phase_registration, game
):
    # Someone registers the victim's number first.
    squat = post(client, game, phone="0559998887", ip="203.0.113.50")
    squatter_link = squat["Location"]
    assert client.get(squatter_link).status_code == 200
    squatter = Player.objects.get(phone="+966559998887")

    admin_client.post(
        "/staff/registration/player/",
        {
            "action": "release_phone",
            "_selected_action": [squatter.pk],
            "confirm": "yes",
            "reason": "owner called, did not register",
        },
    )
    squatter.refresh_from_db()
    assert squatter.phone != "+966559998887"
    assert squatter.registrations.get().status == "removed"
    assert client.get(squatter_link).status_code == 404  # old link is dead

    # The real owner now registers and gets their OWN manage link.
    client.logout()
    owner = post(client, game, phone="0559998887", ip="203.0.113.51")
    assert owner.status_code == 302 and owner["Location"].startswith("/r/")
    log = AuditLog.objects.get(action="player.release_phone")
    assert "559998887" not in str(log.before) + str(log.after)  # no phone in the audit log


def test_operator_actions_are_admin_only(client, game):
    """Even a staff user who was (wrongly) given registration permissions cannot run them."""
    from django.contrib.auth.models import Permission

    regs = _seed_wave(game)
    staff = User.objects.create_user("helper", password="x", is_staff=True)
    staff.user_permissions.set(
        Permission.objects.filter(codename__in=["view_registration", "change_registration"])
    )
    client.force_login(staff)
    client.post(
        "/staff/registration/registration/",
        {
            "action": "remove_registration",
            "_selected_action": [regs["fake-c0"].pk],
            "confirm": "yes",
            "reason": "x",
        },
    )
    assert Registration.objects.get(pk=regs["fake-c0"].pk).status == "confirmed"
    assert not AuditLog.objects.filter(action="registration.remove").exists()
