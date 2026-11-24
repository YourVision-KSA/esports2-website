"""Player entry-badge page /r/<manage_token>/badge/ (entry-badges spec 2026-11-24):
print page for CONFIRMED players only, QR = checkin_token, manage token never leaks.
"""

import pytest

from conftest import set_phase
from core.content import CONTENT
from core.phases import Phase
from registration import services
from registration.models import Registration

pytestmark = pytest.mark.django_db


@pytest.fixture
def confirmed(game):
    set_phase(Phase.REGISTRATION)
    registration, token = services.register(
        full_name="لاعب الاختبار",
        phone="+966551234567",
        email="",
        game=game,
        game_player_id="tag-1",
    )
    return registration, token


def test_badge_page_for_confirmed_player(client, confirmed):
    registration, token = confirmed
    for phase in (Phase.REGISTRATION, Phase.EVENT):
        set_phase(phase)
        response = client.get(f"/r/{token}/badge/")
        assert response.status_code == 200
        body = response.content.decode()
        assert "لاعب الاختبار" in body
        assert registration.game.name_ar in body
        assert "<svg" in body
        assert CONTENT["BADGE_TITLE"] in body
        assert "no-store" in response.headers["Cache-Control"]


def test_badge_qr_is_checkin_token_not_manage_token(client, confirmed, monkeypatch):
    registration, token = confirmed
    seen = []
    from core import qr

    monkeypatch.setattr(qr, "qr_svg", lambda data: seen.append(data) or "<svg></svg>")
    body = client.get(f"/r/{token}/badge/").content.decode()
    assert seen == [registration.player.checkin_token]
    assert token not in body  # the manage secret is never printed on the badge


def test_badge_404_cases(client, confirmed, game):
    registration, token = confirmed
    # Wrong token (uniform 404, same as manage page).
    assert client.get("/r/not-a-real-token/badge/").status_code == 404
    # Too-early phases: badge not reachable.
    for phase in (Phase.PRE, Phase.VOTE, Phase.PERMITS):
        set_phase(phase)
        assert client.get(f"/r/{token}/badge/").status_code == 404
    # Not confirmed: no badge.
    set_phase(Phase.REGISTRATION)
    for status in (Registration.Status.WAITLISTED, Registration.Status.WITHDRAWN):
        Registration.objects.filter(pk=registration.pk).update(status=status)
        assert client.get(f"/r/{token}/badge/").status_code == 404


def test_manage_page_links_to_badge_only_when_confirmed(client, confirmed):
    registration, token = confirmed
    assert "/badge/" in client.get(f"/r/{token}/").content.decode()
    Registration.objects.filter(pk=registration.pk).update(
        status=Registration.Status.WAITLISTED
    )
    assert "/badge/" not in client.get(f"/r/{token}/").content.decode()
