"""Phase derivation and gating (docs/testing.md → Phases & misc)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from conftest import set_phase
from core.models import SiteConfig
from core.phases import Phase, current_phase

pytestmark = pytest.mark.django_db


def _cfg(**kwargs):
    cfg = SiteConfig.get_solo()
    for k, v in kwargs.items():
        setattr(cfg, k, v)
    cfg.save()
    return cfg


def test_phase_derivation_full_timeline():
    now = timezone.now()
    h = timedelta(hours=1)
    cfg = _cfg(
        vote_opens_at=now - 4 * h,
        vote_closes_at=now - 3 * h,
        registration_opens_at=now - 2 * h,
        registration_closes_at=now - 1 * h,
    )
    # Walk a probe time through every boundary.
    assert current_phase(now - 5 * h, cfg) == Phase.PRE
    assert current_phase(now - 4 * h, cfg) == Phase.VOTE  # opens_at INCLUSIVE
    assert current_phase(now - timedelta(hours=3, minutes=30), cfg) == Phase.VOTE
    assert current_phase(now - 3 * h, cfg) == Phase.PERMITS  # closes_at EXCLUSIVE
    assert current_phase(now - 2 * h, cfg) == Phase.REGISTRATION
    assert current_phase(now - 1 * h, cfg) == Phase.EVENT
    cfg.archived = True
    assert current_phase(now, cfg) == Phase.ARCHIVE


def test_unset_datetimes_keep_earlier_phases():
    cfg = _cfg(vote_opens_at=None, vote_closes_at=None)
    assert current_phase(config=cfg) == Phase.PRE


def test_scheduler_not_authoritative(client):
    """Forms close at the configured time with no scheduler involved."""
    set_phase(Phase.PERMITS)  # vote window is over
    response = client.post("/vote/", {})
    assert response.status_code == 403


def test_cached_pages_set_no_cookies(client, db):
    """Edge-cached pages carry no per-visitor state (CLAUDE.md rule 8)."""
    set_phase(Phase.PRE)
    response = client.get("/")
    assert response.status_code == 200
    assert "Set-Cookie" not in response.headers
    assert "max-age=60" in response.headers["Cache-Control"]
    assert b"csrfmiddlewaretoken" not in response.content


def test_bypass_pages_no_store(client, phase_vote, candidate_games):
    response = client.get("/vote/")
    assert "no-store" in response.headers["Cache-Control"]


def test_healthz(client, db):
    assert client.get("/healthz").status_code == 200
