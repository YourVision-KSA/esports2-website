"""Email outbox (docs/data-model.md). Senders queue rows; delivery happens on a
scheduler tick. Uses SELECT ... FOR UPDATE SKIP LOCKED so two concurrent workers
never send the same email twice."""

import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import OutboxEmail

log = logging.getLogger(__name__)


def queue(to_email: str, subject: str, body_text: str) -> OutboxEmail:
    """Insert a queued email. Call inside the caller's transaction so the email
    is queued if-and-only-if the triggering action committed."""
    return OutboxEmail.objects.create(to_email=to_email, subject=subject, body_text=body_text)


def send_due(limit: int = 50) -> int:
    """Send up to `limit` due emails. Returns the number sent. Failures are
    recorded and retried with backoff up to OUTBOX_MAX_ATTEMPTS."""
    now = timezone.now()
    sent = 0
    with transaction.atomic():
        due = (
            OutboxEmail.objects.select_for_update(skip_locked=True)
            .filter(status=OutboxEmail.Status.QUEUED)
            .filter(models_q_due(now))
            .order_by("created_at")[:limit]
        )
        for email in due:
            email.attempts += 1
            try:
                send_mail(
                    email.subject,
                    email.body_text,
                    settings.DEFAULT_FROM_EMAIL,
                    [email.to_email],
                    fail_silently=False,
                )
            except Exception as exc:  # noqa: BLE001 — any SMTP failure is retryable
                email.last_error = str(exc)[:1000]
                # Log the row id only — recipient addresses (and SMTP errors quoting
                # them) stay out of the logs; details live in last_error (admin).
                if email.attempts >= settings.OUTBOX_MAX_ATTEMPTS:
                    email.status = OutboxEmail.Status.FAILED
                    # ERROR so the log-based alert fires (docs/operations.md → Monitoring)
                    log.error(
                        "outbox email %s permanently failed after %s attempts",
                        email.pk,
                        email.attempts,
                    )
                else:
                    # Backoff: 5 min * attempts
                    email.next_attempt_at = now + timedelta(minutes=5 * email.attempts)
                    log.warning(
                        "outbox email %s failed (attempt %s), will retry", email.pk, email.attempts
                    )
            else:
                email.status = OutboxEmail.Status.SENT
                sent += 1
            email.save()
    return sent


def models_q_due(now):
    from django.db.models import Q

    return Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=now)
