"""Server-side Cloudflare Turnstile verification (docs/voting.md flow step 2d).

verify() returns:
  True  — challenge passed
  False — challenge failed
  None  — Turnstile unreachable/timeout

What the caller does with False/None differs (docs/architecture.md → Failure isolation):
the vote puts the ballot in HELD (never rejected); registration rejects and asks the
player to retry (only 48 seats, so a seat must never go to an unchecked request).
"""

import json
import logging
import urllib.parse
import urllib.request

from django.conf import settings

log = logging.getLogger(__name__)

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def verify(token: str, remote_ip: str = "") -> bool | None:
    if not settings.TURNSTILE_ENABLED:
        return True  # local development only; production enables it
    if not token:
        return False
    data = urllib.parse.urlencode(
        {"secret": settings.TURNSTILE_SECRET, "response": token, "remoteip": remote_ip}
    ).encode()
    try:
        with urllib.request.urlopen(SITEVERIFY_URL, data=data, timeout=2) as resp:
            payload = json.load(resp)
        return bool(payload.get("success"))
    except Exception as exc:  # noqa: BLE001 — treat any failure as "unreachable"
        log.warning("turnstile unreachable: %s", exc)
        return None
