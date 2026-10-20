"""Shared pytest fixtures and the concurrency helper (docs/testing.md)."""

import threading
from datetime import timedelta

import pytest
from django.db import connection
from django.utils import timezone

from core.models import Game, SiteConfig
from core.phases import Phase

# ---------------------------------------------------------------------------
# Phase control
# ---------------------------------------------------------------------------


def set_phase(phase: Phase) -> SiteConfig:
    """Arrange SiteConfig datetimes so current_phase() == phase, right now."""
    now = timezone.now()
    hour = timedelta(hours=1)
    cfg = SiteConfig.get_solo()
    cfg.archived = False
    windows = {
        Phase.PRE: (now + hour, now + 2 * hour, now + 3 * hour, now + 4 * hour),
        Phase.VOTE: (now - hour, now + hour, now + 2 * hour, now + 3 * hour),
        Phase.PERMITS: (now - 3 * hour, now - 2 * hour, now + hour, now + 2 * hour),
        Phase.REGISTRATION: (now - 4 * hour, now - 3 * hour, now - hour, now + hour),
        Phase.EVENT: (now - 5 * hour, now - 4 * hour, now - 3 * hour, now - hour),
    }
    if phase == Phase.ARCHIVE:
        cfg.archived = True
        phase = Phase.EVENT  # datetimes don't matter once archived
    (
        cfg.vote_opens_at,
        cfg.vote_closes_at,
        cfg.registration_opens_at,
        cfg.registration_closes_at,
    ) = windows[phase]
    cfg.save()
    return cfg


@pytest.fixture
def phase_vote(db):
    return set_phase(Phase.VOTE)


@pytest.fixture
def phase_registration(db):
    return set_phase(Phase.REGISTRATION)


@pytest.fixture
def phase_event(db):
    return set_phase(Phase.EVENT)


# ---------------------------------------------------------------------------
# Model factories (plain functions — no factory library needed at this size)
# ---------------------------------------------------------------------------


@pytest.fixture
def game(db):
    return Game.objects.create(
        slug="rocket-league",
        name_ar="روكيت ليج",
        name_en="Rocket League",
        status=Game.Status.CONFIRMED,
    )


@pytest.fixture
def candidate_games(db):
    return [
        Game.objects.create(
            slug=f"game-{i}", name_ar=f"لعبة {i}", name_en=f"Game {i}", status=Game.Status.CANDIDATE
        )
        for i in range(1, 6)
    ]


def make_player(i: int, **kwargs):
    from registration.models import Player

    defaults = dict(
        full_name=f"Player {i}",
        phone=f"+96650{i:07d}",
        manage_token_hash=f"testhash{i}",
        consent_at=timezone.now(),
    )
    defaults.update(kwargs)
    return Player.objects.create(**defaults)


def fill_confirmed(game: Game, n: int):
    """Create n players with confirmed registrations for `game`."""
    from registration.models import Registration

    return [
        Registration.objects.create(
            player=make_player(1000 + i),
            game=game,
            status=Registration.Status.CONFIRMED,
            game_player_id=f"tag{1000 + i}",
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Concurrency helper
# ---------------------------------------------------------------------------


def run_concurrently(*fns):
    """Run callables in parallel threads, synchronized at a barrier so they hit
    the critical section together. Returns [(result, exception), ...] in order.
    Use with @pytest.mark.django_db(transaction=True) — each thread gets its own
    DB connection, closed on exit."""
    barrier = threading.Barrier(len(fns))
    results: list = [None] * len(fns)

    def runner(idx, fn):
        try:
            barrier.wait(timeout=10)
            results[idx] = (fn(), None)
        except Exception as exc:  # noqa: BLE001 — tests inspect the exception
            results[idx] = (None, exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=runner, args=(i, fn)) for i, fn in enumerate(fns)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    return results
