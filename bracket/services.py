"""Result entry and correction (docs/data-model.md). Both are transactions with
row locks and audit records; the winner advances into the next match's slot."""

from django.core.exceptions import ValidationError
from django.db import transaction

from core import audit

from .models import Match


class CorrectionBlocked(Exception):
    """Downstream match already played — manual admin intervention required."""


def _propagate(match: Match, registration):
    if match.next_match_id:
        nxt = Match.objects.select_for_update().get(pk=match.next_match_id)
        field = "player1" if match.next_slot == 1 else "player2"
        setattr(nxt, field, registration)
        nxt.save(update_fields=[field])


def enter_result(match: Match, winner, score_text: str, actor) -> Match:
    """Record a result on a pending match and advance the winner."""
    with transaction.atomic():
        match = Match.objects.select_for_update().get(pk=match.pk)
        if match.status != Match.Status.PENDING:
            raise ValidationError("match is not pending")
        if winner.pk not in (match.player1_id, match.player2_id):
            raise ValidationError("winner must be one of the participants")
        before = {"winner": match.winner_id, "score": match.score_text, "status": match.status}
        match.winner = winner
        match.score_text = score_text
        match.status = Match.Status.DONE
        match.save()
        _propagate(match, winner)
        audit.record(
            actor,
            "result.enter",
            match,
            before=before,
            after={"winner": winner.pk, "score": score_text, "status": "done"},
        )
    return match


def correct_result(match: Match, new_winner, score_text: str, actor) -> Match:
    """Admin-only correction. Allowed only while the downstream match is still
    pending; otherwise refuse and log the attempt (docs/data-model.md)."""
    blocked = False
    with transaction.atomic():
        match = Match.objects.select_for_update().get(pk=match.pk)
        if match.status == Match.Status.PENDING:
            raise ValidationError("match has no result to correct")
        if new_winner.pk not in (match.player1_id, match.player2_id):
            raise ValidationError("winner must be one of the participants")
        if match.next_match_id:
            nxt = Match.objects.select_for_update().get(pk=match.next_match_id)
            if nxt.status != Match.Status.PENDING:
                blocked = True
    if blocked:
        # Logged OUTSIDE the atomic block so the record survives the refusal.
        audit.record(
            actor, "result.correct_blocked", match, after={"attempted_winner": new_winner.pk}
        )
        raise CorrectionBlocked
    with transaction.atomic():
        match = Match.objects.select_for_update().get(pk=match.pk)
        before = {"winner": match.winner_id, "score": match.score_text}
        match.winner = new_winner
        match.score_text = score_text
        match.save()
        _propagate(match, new_winner)
        audit.record(
            actor,
            "result.correct",
            match,
            before=before,
            after={"winner": new_winner.pk, "score": score_text},
        )
    return match
