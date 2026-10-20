"""Check-in: race-safe single use (docs/data-model.md). The conditional UPDATE
guarantees exactly one concurrent scan succeeds."""

from django.utils import timezone

from core import audit

from .models import Invitation


class CheckInResult:
    OK = "ok"
    ALREADY = "already"
    INVALID = "invalid"


def check_in(token: str, actor) -> tuple[str, Invitation | None]:
    """Returns (result, invitation). ALREADY includes who/when for the door staff."""
    updated = Invitation.objects.filter(token=token, status=Invitation.Status.SENT).update(
        status=Invitation.Status.CHECKED_IN,
        checked_in_at=timezone.now(),
        checked_in_by=actor,
    )
    invitation = Invitation.objects.filter(token=token).first()
    if updated == 1:
        audit.record(actor, "invitation.checkin", invitation)
        return CheckInResult.OK, invitation
    if invitation and invitation.status == Invitation.Status.CHECKED_IN:
        return CheckInResult.ALREADY, invitation
    return CheckInResult.INVALID, None
