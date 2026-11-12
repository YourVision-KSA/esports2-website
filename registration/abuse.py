"""Application-side limits on the public registration form (audit 2026-11-13, finding 1).

Cloudflare rate rules are the first line (docs/operations.md); these limits hold even if
an edge rule is missing. Every POST is recorded as a RegistrationAttempt (hashes only),
and a request is refused when any of these counts is already at its limit:

  REG_IP_ATTEMPTS_PER_10MIN       POSTs from one client IP in 10 minutes
                                  (refused attempts are not counted, so a person who
                                  waits a few minutes gets through again)
  REG_PHONE_ATTEMPTS_PER_DAY      POSTs naming one phone number in 24 hours — slows down
                                  probing which numbers are registered
  REG_IP_REGISTRATIONS_PER_DAY    successful registrations from one client IP in 24 hours
  REG_DEVICE_REGISTRATIONS_PER_DAY  successful registrations from one IP + user agent

The counts are plain indexed SQL counts (no Redis — docs/architecture.md). Two requests
racing past a check can exceed a limit by one or two; that is acceptable for a soft limit
and keeps the seat transaction free of extra locks.
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from core.security import client_ip, hmac_hash

from .models import RegistrationAttempt

Outcome = RegistrationAttempt.Outcome


def client_hashes(request) -> tuple[str, str]:
    """(ip_hash, ua_hash) of the trusted client address — never the raw values."""
    return hmac_hash(client_ip(request)), hmac_hash(request.headers.get("User-Agent", ""))


def phone_hash(normalized_phone: str) -> str:
    return hmac_hash(normalized_phone)


def _recent(since_delta, **filters):
    since = timezone.now() - since_delta
    return RegistrationAttempt.objects.filter(created_at__gte=since, **filters)


def ip_attempts_exceeded(ip_hash: str) -> bool:
    n = _recent(timedelta(minutes=10), ip_hash=ip_hash).exclude(outcome=Outcome.LIMITED).count()
    return n >= settings.REG_IP_ATTEMPTS_PER_10MIN


def phone_attempts_exceeded(p_hash: str) -> bool:
    n = _recent(timedelta(days=1), phone_hash=p_hash).exclude(outcome=Outcome.LIMITED).count()
    return n >= settings.REG_PHONE_ATTEMPTS_PER_DAY


def registrations_exceeded(ip_hash: str, ua_hash: str) -> bool:
    ok = _recent(timedelta(days=1), ip_hash=ip_hash, outcome=Outcome.REGISTERED)
    if ok.count() >= settings.REG_IP_REGISTRATIONS_PER_DAY:
        return True
    return ok.filter(ua_hash=ua_hash).count() >= settings.REG_DEVICE_REGISTRATIONS_PER_DAY
