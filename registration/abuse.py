"""Application-side limits on the public registration form (audit 2026-11-13, finding 1;
security assessment 2026-11-19, YV-06 and YV-07).

Cloudflare rate rules are the first line (docs/operations.md); these limits hold even if
an edge rule is missing. Every POST is recorded as a RegistrationAttempt (hashes only),
and a request is refused when any of these counts is already at its limit:

  REG_IP_ATTEMPTS_PER_10MIN       VERIFIED attempts from one client network in 10 minutes:
                                  only attempts that passed form validation AND Turnstile
                                  count (outcomes registered / duplicate / full). Most
                                  players share the campus NAT, so if garbage or unsolved
                                  POSTs counted, one person could lock registration for
                                  the whole campus at no cost (YV-06).
  REG_IP_FLOOD_PER_10MIN          all NON-REFUSED attempts from one client network in 10
                                  minutes — a much higher anti-flood ceiling for raw POSTs
                                  (costs a real campus nothing at the default). It stops
                                  the processing of a flood (Turnstile calls, form work),
                                  not the recording: every refused POST still writes one
                                  LIMITED row, and LIMITED rows are excluded from this
                                  count so the ceiling clears by itself after the flood.
  REG_PHONE_ATTEMPTS_PER_DAY      POSTs naming one phone number in 24 hours — slows down
                                  probing which numbers are registered. Only attempts
                                  that PASSED Turnstile count: the limit is checked
                                  before Turnstile, so if bot-check failures counted, a
                                  script with no Turnstile solution could use up a
                                  stranger's number and lock them out for a day
  REG_IP_REGISTRATIONS_PER_DAY    successful registrations from one client network in 24 h
  REG_DEVICE_REGISTRATIONS_PER_DAY  successful registrations from one network + user agent

Refused attempts (LIMITED) never count, so a person who waits gets through again.

"Client network" (core.security.network_key) is the address for IPv4 and the /64 for
IPv6: one IPv6 line is a whole /64, and keying on the exact address let a single person
rotate addresses past every limit (YV-07). RegistrationAttempt.ip_hash stores the HMAC of
that network, not of the address.

The counts are plain indexed SQL counts (no Redis — docs/architecture.md). Two requests
racing past a check can exceed a limit by one or two; that is acceptable for a soft limit
and keeps the seat transaction free of extra locks.
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from core.security import client_ip, hmac_hash, network_hash

from .models import RegistrationAttempt

Outcome = RegistrationAttempt.Outcome


def client_hashes(request) -> tuple[str, str]:
    """(ip_hash, ua_hash): HMAC of the trusted client's NETWORK (IPv6 /64) and of the
    user agent — never the raw values."""
    return network_hash(client_ip(request)), hmac_hash(request.headers.get("User-Agent", ""))


def phone_hash(normalized_phone: str) -> str:
    return hmac_hash(normalized_phone)


def _recent(since_delta, **filters):
    since = timezone.now() - since_delta
    return RegistrationAttempt.objects.filter(created_at__gte=since, **filters)


# Outcomes that are only reached after the form validated AND Turnstile passed.
VERIFIED_OUTCOMES = (Outcome.REGISTERED, Outcome.DUPLICATE, Outcome.FULL)


def ip_attempts_exceeded(ip_hash: str) -> bool:
    """Network limits, checked before anything else on a POST (see module docstring)."""
    recent = _recent(timedelta(minutes=10), ip_hash=ip_hash)
    if recent.filter(outcome__in=VERIFIED_OUTCOMES).count() >= settings.REG_IP_ATTEMPTS_PER_10MIN:
        return True
    return recent.exclude(outcome=Outcome.LIMITED).count() >= settings.REG_IP_FLOOD_PER_10MIN


def phone_attempts_exceeded(p_hash: str) -> bool:
    # Not counted: refused attempts (LIMITED) and attempts that failed the bot check
    # (TURNSTILE) — see the module docstring. What is left needed a solved Turnstile.
    not_counted = (Outcome.LIMITED, Outcome.TURNSTILE)
    n = _recent(timedelta(days=1), phone_hash=p_hash).exclude(outcome__in=not_counted).count()
    return n >= settings.REG_PHONE_ATTEMPTS_PER_DAY


def registrations_exceeded(ip_hash: str, ua_hash: str) -> bool:
    ok = _recent(timedelta(days=1), ip_hash=ip_hash, outcome=Outcome.REGISTERED)
    if ok.count() >= settings.REG_IP_REGISTRATIONS_PER_DAY:
        return True
    return ok.filter(ua_hash=ua_hash).count() >= settings.REG_DEVICE_REGISTRATIONS_PER_DAY
