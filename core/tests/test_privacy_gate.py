"""Registration stays closed while the privacy notice has [placeholders] (audit
2026-11-13, finding 4). Tests marked real_privacy_notice see the real strings; the
others run as if the owner had filled them (conftest.py)."""

from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from core import privacy
from core.admin import SiteConfigForm
from core.content import CONTENT
from core.models import SiteConfig
from registration.models import Player, Registration

pytestmark = pytest.mark.django_db

REG_POST = {
    "full_name": "لاعب",
    "phone": "0551234567",
    "email": "",
    "game_player_id": "tag",
    "consent": "on",
}


@pytest.mark.real_privacy_notice
def test_current_notice_placeholders_are_found():
    keys = {key for key, _ in privacy.unfilled_placeholders()}
    # the gaps named in the audit: date, controller+contact, hosting, retention, under-18
    assert {
        "PRIVACY-UPDATED",
        "PRIVACY-S1-P1",
        "PRIVACY-S6-P1",
        "PRIVACY-S7-P1",
        "PRIVACY-S9-P1",
    } <= keys


@pytest.mark.real_privacy_notice
def test_registration_closed_while_placeholders_remain(client, phase_registration, game):
    choose = client.get("/register/")
    assert CONTENT["REG_CLOSED"] in choose.content.decode()
    form = client.get(f"/register/{game.slug}/")
    assert CONTENT["REG_CLOSED"] in form.content.decode()
    assert "csrfmiddlewaretoken" not in form.content.decode()  # no form is served
    assert client.post(f"/register/{game.slug}/", REG_POST).status_code == 403
    assert not Player.objects.exists() and not Registration.objects.exists()


def test_registration_open_once_the_notice_is_complete(client, phase_registration, game):
    assert client.post(f"/register/{game.slug}/", REG_POST).status_code == 302


@pytest.mark.real_privacy_notice
def test_siteconfig_admin_refuses_to_schedule_registration(phase_registration):
    cfg = SiteConfig.get_solo()
    data = {
        "vote_opens_at": "2026-11-01 10:00",
        "vote_closes_at": "2026-11-08 10:00",
        "registration_opens_at": "2026-11-16 10:00",
    }
    form = SiteConfigForm(data=data, instance=cfg)
    assert not form.is_valid()
    message = " ".join(form.errors["registration_opens_at"])
    assert "privacy notice" in message and "PRIVACY-S1-P1" in message


@pytest.mark.real_privacy_notice
def test_check_privacy_command_lists_placeholders_and_fails():
    out = StringIO()
    with pytest.raises(CommandError, match="placeholder"):
        call_command("check_privacy", stdout=out)
    assert "PRIVACY-S9-P1" in out.getvalue()


def test_check_privacy_command_passes_when_complete():
    out = StringIO()
    call_command("check_privacy", stdout=out)
    assert "complete" in out.getvalue()


def test_placeholder_detection():
    assert privacy.PLACEHOLDER.findall("نحذف خلال [30–90] يومًا") == ["[30–90]"]
    assert privacy.PLACEHOLDER.findall("لا شيء هنا") == []


# ---- pre-merge review: the admin check only guards the registration date itself


def _siteconfig_post(cfg, **changes):
    """What the admin form submits for `cfg`, with some fields changed."""
    data = {
        name: getattr(cfg, name) or ""
        for name in SiteConfigForm.Meta.fields
        if name != "archived"  # unchecked checkbox = absent
    }
    data.update(changes)
    return data


@pytest.mark.real_privacy_notice
def test_siteconfig_with_a_saved_registration_date_can_still_be_edited(phase_registration):
    """A registration date was saved earlier (e.g. before the gate existed). Staff must
    still be able to change other fields while the notice is unfinished."""
    cfg = SiteConfig.get_solo()
    form = SiteConfigForm(
        data=_siteconfig_post(cfg, stream_url_1="https://example.com/live"), instance=cfg
    )
    assert form.is_valid(), form.errors
    form.save()
    assert SiteConfig.get_solo().stream_url_1 == "https://example.com/live"


@pytest.mark.real_privacy_notice
def test_siteconfig_admin_refuses_to_move_a_saved_registration_date(phase_registration):
    cfg = SiteConfig.get_solo()
    form = SiteConfigForm(
        data=_siteconfig_post(cfg, registration_opens_at="2026-11-20 10:00"), instance=cfg
    )
    assert not form.is_valid()
    assert "privacy notice" in " ".join(form.errors["registration_opens_at"])


@pytest.mark.real_privacy_notice
def test_siteconfig_registration_date_can_be_cleared(phase_registration):
    cfg = SiteConfig.get_solo()
    form = SiteConfigForm(data=_siteconfig_post(cfg, registration_opens_at=""), instance=cfg)
    assert form.is_valid(), form.errors


# ---- pre-merge review: the home page's Register links follow the same gate


@pytest.mark.real_privacy_notice
def test_home_has_no_register_links_while_the_gate_keeps_registration_closed(
    client, phase_registration, game
):
    body = client.get("/").content.decode()
    assert 'href="/register/' not in body


def test_home_links_to_registration_once_the_notice_is_complete(client, phase_registration, game):
    body = client.get("/").content.decode()
    assert 'href="/register/"' in body
    assert f'href="/register/{game.slug}/"' in body
