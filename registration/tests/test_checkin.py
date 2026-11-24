"""Player door check-in (docs/testing.md → Invitations / check-in, player rows):
single-use, race-safe, only players holding a CONFIRMED seat get through the gate.
"""

import pytest
from django.contrib.auth.models import User

from conftest import run_concurrently
from core.models import AuditLog
from invitations.services import CheckInResult
from registration import services
from registration.models import Player, Registration

pytestmark = pytest.mark.django_db


@pytest.fixture
def door_user(db):
    return User.objects.create_user("door1", password="x", is_staff=True)


def make_player(game, status=Registration.Status.CONFIRMED, i=1):
    registration, _ = services.register(
        full_name=f"P{i}",
        phone=f"+96655{i:07d}",
        email="",
        game=game,
        game_player_id=f"tag-{i}",
    )
    if registration.status != status:
        Registration.objects.filter(pk=registration.pk).update(status=status)
    return registration.player


def test_checkin_marks_confirmed_player(game, door_user):
    player = make_player(game)
    result, checked = services.check_in(player.checkin_token, door_user)
    assert result == CheckInResult.OK
    assert checked.pk == player.pk
    player.refresh_from_db()
    assert player.checked_in_at is not None
    assert player.checked_in_by == door_user
    assert AuditLog.objects.filter(action="player.checkin", object_id=str(player.pk)).count() == 1


def test_checkin_requires_confirmed_registration(game, door_user):
    for i, status in enumerate(
        (
            Registration.Status.WAITLISTED,
            Registration.Status.WITHDRAWN,
            Registration.Status.REMOVED,
        ),
        start=1,
    ):
        player = make_player(game, status=status, i=i)
        assert services.check_in(player.checkin_token, door_user) == (CheckInResult.INVALID, None)
    # A player row with no registration at all (defensive), and an unknown token.
    bare = Player.objects.create(
        full_name="بدون تسجيل",
        phone="+966550009999",
        manage_token_hash=Player.hash_token("x" * 24),
        consent_at="2026-11-01T00:00:00Z",
    )
    assert services.check_in(bare.checkin_token, door_user) == (CheckInResult.INVALID, None)
    unknown = services.check_in("totally-unknown-token-000", door_user)
    assert unknown == (CheckInResult.INVALID, None)


def test_checkin_already_reports_time_and_actor(game, door_user):
    player = make_player(game)
    services.check_in(player.checkin_token, door_user)
    player.refresh_from_db()
    first_at, first_by = player.checked_in_at, player.checked_in_by
    other = User.objects.create_user("door2", password="x", is_staff=True)
    result, checked = services.check_in(player.checkin_token, other)
    assert result == CheckInResult.ALREADY
    assert checked.checked_in_at == first_at
    assert checked.checked_in_by == first_by


@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
def test_checkin_single_use_concurrent(game, door_user):
    player = make_player(game)
    results = run_concurrently(
        lambda: services.check_in(player.checkin_token, door_user),
        lambda: services.check_in(player.checkin_token, door_user),
    )
    outcomes = sorted(r[0] for r, exc in results if exc is None)
    assert outcomes == [CheckInResult.ALREADY, CheckInResult.OK]
    player.refresh_from_db()
    assert player.checked_in_at is not None


def test_undo_checkin_rearms_token(game, door_user):
    player = make_player(game)
    services.check_in(player.checkin_token, door_user)
    player.refresh_from_db()
    undone = services.undo_checkin(player, door_user)
    assert undone.checked_in_at is None and undone.checked_in_by is None
    assert AuditLog.objects.filter(
        action="player.checkin_reversed", object_id=str(player.pk)
    ).exists()
    result, _ = services.check_in(player.checkin_token, door_user)
    assert result == CheckInResult.OK
