"""Voting fixes from the 2026-11-13 audit: no 500 on odd digits, ballot status changes
only through audited actions, and the promised 14-day strip of ballot signals."""

from datetime import timedelta

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from conftest import set_phase
from core.models import AuditLog, SiteConfig
from core.phases import Phase
from voting import services
from voting.models import Ballot

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("value", ["²", "١٢٣٤٥٦٧٨٩٠١٢٣٤٥٦٧٨٩٠١٢٣٤٥٦٧٨٩", "99999999999999999999999"])
def test_unusual_digits_in_choices_do_not_crash(client, candidate_games, value):
    set_phase(Phase.VOTE)
    client.get("/vote/")  # voter cookie
    response = client.post("/vote/", {"choices": [value]})
    assert response.status_code == 400  # invalid ballot, not a 500
    assert not Ballot.objects.exists()


def _ballot(candidate_games, status=Ballot.Status.HELD):
    ballot = services.cast_ballot(
        voter_token="t",
        choice_ids=[g.pk for g in candidate_games[:3]],
        turnstile_ok=False,
        ip="203.0.113.1",
        ua="UA",
    )
    assert ballot.status == status
    return ballot


def test_ballot_status_cannot_be_edited_on_the_change_form(admin_client, candidate_games):
    ballot = _ballot(candidate_games)
    admin_client.post(
        f"/staff/voting/ballot/{ballot.pk}/change/",
        {
            "status": "counted",
            "held_reason": "",
            "invalidated_reason": "",
            "choices-TOTAL_FORMS": "3",
            "choices-INITIAL_FORMS": "3",
            "choices-MIN_NUM_FORMS": "0",
            "choices-MAX_NUM_FORMS": "1000",
            **{f"choices-{i}-id": c.pk for i, c in enumerate(ballot.choices.all())},
            **{f"choices-{i}-ballot": ballot.pk for i in range(3)},
        },
    )
    ballot.refresh_from_db()
    assert ballot.status == Ballot.Status.HELD
    # the audited bulk action is the way
    admin_client.post(
        "/staff/voting/ballot/", {"action": "mark_counted", "_selected_action": [ballot.pk]}
    )
    ballot.refresh_from_db()
    assert ballot.status == Ballot.Status.COUNTED
    assert AuditLog.objects.filter(action="ballot.count", object_id=str(ballot.pk)).exists()


def test_strip_vote_signals_waits_14_days_after_close(candidate_games):
    ballot = _ballot(candidate_games)
    assert ballot.signals
    cfg = SiteConfig.get_solo()
    cfg.vote_closes_at = timezone.now() - timedelta(days=13)
    cfg.save()
    with pytest.raises(CommandError, match="14 days"):
        call_command("strip_vote_signals")
    ballot.refresh_from_db()
    assert ballot.signals

    cfg.vote_closes_at = timezone.now() - timedelta(days=15)
    cfg.save()
    call_command("strip_vote_signals")
    ballot.refresh_from_db()
    assert ballot.signals is None
    assert ballot.status == Ballot.Status.HELD and ballot.ip_hash  # audit data kept
    assert AuditLog.objects.filter(action="ballot.strip_signals").exists()
