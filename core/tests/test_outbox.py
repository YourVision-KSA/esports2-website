"""Outbox delivery: retries, and SKIP LOCKED under concurrency (docs/testing.md)."""

import pytest
from django.test import override_settings

from conftest import run_concurrently
from core import outbox
from core.models import OutboxEmail


@pytest.mark.django_db
def test_send_due_marks_sent():
    outbox.queue("a@example.com", "s", "b")
    assert outbox.send_due() == 1
    email = OutboxEmail.objects.get()
    assert email.status == OutboxEmail.Status.SENT
    assert email.attempts == 1


@pytest.mark.django_db
@override_settings(EMAIL_BACKEND="core.tests.test_outbox.FailingBackend")
def test_send_failure_schedules_retry_then_fails():
    outbox.queue("a@example.com", "s", "b")
    assert outbox.send_due() == 0
    email = OutboxEmail.objects.get()
    assert email.status == OutboxEmail.Status.QUEUED
    assert email.attempts == 1
    assert email.next_attempt_at is not None
    # Exhaust the attempts: force due and resend until FAILED.
    for _ in range(10):
        OutboxEmail.objects.update(next_attempt_at=None)
        outbox.send_due()
    email.refresh_from_db()
    assert email.status == OutboxEmail.Status.FAILED
    assert email.attempts == 5  # OUTBOX_MAX_ATTEMPTS


class FailingBackend:
    def __init__(self, *args, **kwargs):
        pass

    def send_messages(self, messages):
        raise OSError("smtp down")

    def open(self):
        pass

    def close(self):
        pass


@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
def test_outbox_skip_locked():
    """Two workers ticking at once never send the same email twice."""
    for i in range(6):
        outbox.queue(f"user{i}@example.com", "s", "b")
    results = run_concurrently(outbox.send_due, outbox.send_due)
    sent_counts = [r for r, exc in results]
    assert all(exc is None for _, exc in results)
    assert sum(sent_counts) == 6
    assert not OutboxEmail.objects.exclude(attempts=1).exists()
