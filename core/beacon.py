"""Count-only beacon for the hero 3D quality tiers (docs/frontend.md → Quality tiers).

The browser sends at most one beacon per tab session (frontend/src/hero.js) with two
values from fixed lists. Nothing that identifies a visitor is read or stored."""

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from .models import TierStat

OUTCOMES = set(TierStat.Outcome.values)
DEVICES = set(TierStat.Device.values)


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
