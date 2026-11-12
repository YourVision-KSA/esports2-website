"""Check-in: race-safe single use (docs/data-model.md). The conditional UPDATE
guarantees exactly one concurrent scan succeeds."""

from django.db import transaction
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


# ---------------------------------------------------------------------------------------
# Admin-side state changes (audit 2026-11-13, finding 2). The Django admin never edits
# Invitation.status directly; these are the only other ways the status moves, and each
# one writes an AuditLog row with before/after. Contact details are never logged.
# ---------------------------------------------------------------------------------------


def _transition(invitation_id, actor, action, allowed_from, to_status, **extra_fields):
    """Conditional single-row UPDATE (same pattern as check_in): only rows still in an
    allowed status change, so two staff acting at once cannot double-apply."""
    with transaction.atomic():
        invitation = Invitation.objects.select_for_update().filter(pk=invitation_id).first()
        if invitation is None or invitation.status not in allowed_from:
            return None
        before = invitation.status
        invitation.status = to_status
        for name, value in extra_fields.items():
            setattr(invitation, name, value)
        invitation.save(update_fields=["status", *extra_fields, "updated_at"])
        audit.record(
            actor, action, invitation, before={"status": before}, after={"status": to_status}
        )
        return invitation


def mark_sent(invitation: Invitation, actor) -> Invitation | None:
    """CREATED → SENT and queue the invitation email (same transaction)."""
    from core import outbox
    from core.content import CONTENT

    with transaction.atomic():
        updated = _transition(
            invitation.pk,
            actor,
            "invitation.sent",
            {Invitation.Status.CREATED},
            Invitation.Status.SENT,
            sent_at=timezone.now(),
        )
        if updated and updated.contact_email:
            outbox.queue(
                updated.contact_email,
                CONTENT["INVITE_TITLE"],
                f"{CONTENT['INVITE_BODY']}\n\n{updated.invite_url()}",
            )
        return updated


def revoke(invitation: Invitation, actor) -> Invitation | None:
    """CREATED/SENT → REVOKED. A checked-in invitation cannot be revoked."""
    return _transition(
        invitation.pk,
        actor,
        "invitation.revoke",
        {Invitation.Status.CREATED, Invitation.Status.SENT},
        Invitation.Status.REVOKED,
    )


def undo_checkin(invitation: Invitation, actor) -> Invitation | None:
    """CHECKED_IN → SENT, for a check-in recorded by mistake (admin only; the reversal
    named in docs/data-model.md → AuditLog). The QR code works again afterwards."""
    return _transition(
        invitation.pk,
        actor,
        "invitation.checkin_reversed",
        {Invitation.Status.CHECKED_IN},
        Invitation.Status.SENT,
        checked_in_at=None,
        checked_in_by=None,
    )
