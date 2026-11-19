"""Count-only beacon for the hero 3D quality tiers (docs/frontend.md → Quality tiers).

The browser sends at most one beacon per tab session (frontend/src/hero.js) with two
values from fixed lists. Nothing that identifies a visitor is stored.

Per-network limit (security assessment 2026-11-19, critic): the endpoint is CSRF-exempt
by necessity, so without a limit anyone could inflate the counters behind tier_report.
The Cloudflare rate rule is the first line, but this limit holds without it:
BEACON_PER_NETWORK_10MIN beacons per client network (core.security.network_key: the
address for IPv4, the /64 for IPv6) per fixed 10-minute window. It lives in the
process's memory (Django's default local-memory cache — no Redis, docs/architecture.md),
so it costs no database query; with several Cloud Run instances the effective limit is
that number per instance, which is fine for a statistics counter.
"""

import time

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .models import TierStat
from .security import client_ip, network_hash

OUTCOMES = set(TierStat.Outcome.values)
DEVICES = set(TierStat.Device.values)


BEACON_WINDOW_SECONDS = 600


def beacon_allowed(request) -> bool:
    """Count this beacon against its network's window; False once over the limit.
    The cache key holds only the HMAC of the network, never the address."""
    window = int(time.time() // BEACON_WINDOW_SECONDS)
    key = f"beacon:{network_hash(client_ip(request))}:{window}"
    cache.add(key, 0, timeout=BEACON_WINDOW_SECONDS + 60)
    try:
        n = cache.incr(key)
    except ValueError:  # evicted between add() and incr(): start again at 1
        cache.set(key, 1, timeout=BEACON_WINDOW_SECONDS + 60)
        n = 1
    return n <= settings.BEACON_PER_NETWORK_10MIN


def record_tier(outcome: str, device: str) -> bool:
    """Add one to today's counter. Returns False (and writes nothing) for unknown values.

    Race-safe without locks: UPDATE … SET count = count + 1; if no row exists yet, INSERT;
    if two requests insert at once, the loser hits the unique constraint and retries the
    UPDATE (which now finds the row)."""
    if outcome not in OUTCOMES or device not in DEVICES:
        return False
    day = timezone.localdate()  # Asia/Riyadh day boundaries
    key = {"day": day, "outcome": outcome, "device": device}
    if TierStat.objects.filter(**key).update(count=F("count") + 1):
        return True
    try:
        with transaction.atomic():
            TierStat.objects.create(**key, count=1)
    except IntegrityError:
        TierStat.objects.filter(**key).update(count=F("count") + 1)
    return True
