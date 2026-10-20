"""Bracket critical tests (docs/testing.md → Bracket): draw, result entry,
corrections, permissions."""

import pytest
from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.core.management import call_command

from bracket import services
from bracket.draw import draw
from bracket.models import Match
from conftest import fill_confirmed
from core.models import AuditLog

pytestmark = pytest.mark.django_db


@pytest.fixture
def referee(db):
    call_command("setup_roles")
    user = User.objects.create_user("ref1", password="x", is_staff=True)
    user.groups.add(Group.objects.get(name="referee"))
    return User.objects.get(pk=user.pk)  # refresh perm cache


def test_draw_seeds_16(game):
    fill_confirmed(game, 16)
    matches = draw(game, seed=42)
    assert len(matches) == 15
    r1 = [m for m in matches if m.round == 1]
    assert len(r1) == 8
    players = [m.player1_id for m in r1] + [m.player2_id for m in r1]
    assert len(set(players)) == 16  # every player exactly once
    assert AuditLog.objects.filter(action="bracket.draw").exists()


def test_draw_deterministic_under_seed(game):
    fill_confirmed(game, 16)
    pairs1 = [(m.player1_id, m.player2_id) for m in draw(game, seed=7) if m.round == 1]
    game.matches.all().delete()
    pairs2 = [(m.player1_id, m.player2_id) for m in draw(game, seed=7) if m.round == 1]
    assert pairs1 == pairs2


def test_draw_refuses_second_run(game):
    fill_confirmed(game, 16)
    draw(game, seed=1)
    with pytest.raises(ValueError):
        draw(game, seed=1)


def test_draw_with_byes(game):
    fill_confirmed(game, 14)
    matches = draw(game, seed=1)
    byes = [m for m in matches if m.round == 1 and m.status == Match.Status.FORFEIT]
    assert len(byes) == 2
    for bye in byes:
        nxt = bye.next_match
        nxt.refresh_from_db()
        slot_player = nxt.player1 if bye.next_slot == 1 else nxt.player2
        assert slot_player == bye.winner  # forfeit win propagated


def _played_bracket(game):
    fill_confirmed(game, 16)
    draw(game, seed=42)
    return Match.objects.get(game=game, round=1, slot=1)


def test_result_advances_winner(game, referee):
    match = _played_bracket(game)
    winner = match.player1
    services.enter_result(match, winner, "3–1", actor=referee)
    match.refresh_from_db()
    assert match.status == Match.Status.DONE
    nxt = match.next_match
    nxt.refresh_from_db()
    assert (nxt.player1 if match.next_slot == 1 else nxt.player2) == winner
    log = AuditLog.objects.get(action="result.enter")
    assert log.before["winner"] is None
    assert log.after["winner"] == winner.pk


def test_winner_must_be_participant(game, referee):
    match = _played_bracket(game)
    outsider = Match.objects.get(game=game, round=1, slot=2).player1
    with pytest.raises(ValidationError):
        services.enter_result(match, outsider, "3–0", actor=referee)


def test_double_entry_refused(game, referee):
    match = _played_bracket(game)
    services.enter_result(match, match.player1, "3–1", actor=referee)
    with pytest.raises(ValidationError):
        services.enter_result(match, match.player2, "1–3", actor=referee)


def test_result_correction_pending_downstream(game, referee, admin_user):
    match = _played_bracket(game)
    services.enter_result(match, match.player1, "3–1", actor=referee)
    services.correct_result(match, match.player2, "1–3", actor=admin_user)
    match.refresh_from_db()
    nxt = match.next_match
    nxt.refresh_from_db()
    assert (nxt.player1 if match.next_slot == 1 else nxt.player2) == match.player2
    assert AuditLog.objects.filter(action="result.correct").exists()


def test_result_correction_blocked_downstream_done(game, referee, admin_user):
    m1 = _played_bracket(game)
    m2 = Match.objects.get(game=game, round=1, slot=2)
    services.enter_result(m1, m1.player1, "3–1", actor=referee)
    services.enter_result(m2, m2.player1, "3–2", actor=referee)
    nxt = m1.next_match
    nxt.refresh_from_db()
    services.enter_result(nxt, nxt.player1, "3–0", actor=referee)  # downstream done
    with pytest.raises(services.CorrectionBlocked):
        services.correct_result(m1, m1.player2, "0–3", actor=admin_user)
    assert AuditLog.objects.filter(action="result.correct_blocked").exists()


def test_referee_permission_boundaries(referee):
    assert referee.has_perm("bracket.change_match")
    assert not referee.has_perm("core.change_siteconfig")
    assert not referee.has_perm("registration.view_player")


def test_staff_results_requires_permission(client, game, phase_event):
    User.objects.create_user("nobody", password="x", is_staff=True)
    client.login(username="nobody", password="x")
    assert client.get("/staff/results/").status_code == 403


def test_api_bracket_no_pii(client, game, phase_event, referee):
    fill_confirmed(game, 16)
    draw(game, seed=1)
    data = client.get(f"/api/bracket/{game.slug}.json").json()
    assert len(data["matches"]) == 15
    body = str(data)
    assert "+9665" not in body  # gamer tags only, never phones/names
    assert "Player 10" not in body
