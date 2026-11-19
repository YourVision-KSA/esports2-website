"""Ballot casting and classification (docs/voting.md).

Classification sets status counted/held with cheap synchronous checks only.
HELD is a review bucket, not a rejection: the voter sees the same success page.
"""

from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import Game
from core.security import hmac_hash, network_hash, token_hash

from .asns import DATACENTER_ASNS
from .models import Ballot, BallotChoice


class AlreadyVoted(Exception):
    pass


class InvalidChoices(Exception):
    pass


def classify(
    *, turnstile_ok: bool | None, asn: int | None, ip_hash: str, ua_hash: str, now=None
) -> tuple[str, str]:
    """Return (status, held_reason). Order per docs/voting.md: cheapest first.

    The burst counts include only ballots that PASSED Turnstile (security assessment
    2026-11-19, YV-34): a ballot without a solved challenge is already HELD for that
    reason, and if it counted here, five token-less POSTs from the campus NAT would push
    every real voter on that network into HELD for an hour.

    Call it inside cast_ballot's transaction, after the per-network lock (YV-35)."""
    now = now or timezone.now()
    if turnstile_ok is not True:
        return Ballot.Status.HELD, "turnstile"
    if asn and asn in DATACENTER_ASNS:
        return Ballot.Status.HELD, "datacenter"
    verified = Ballot.objects.filter(ip_hash=ip_hash, turnstile_passed=True)
    hour_ago = now - timedelta(hours=1)
    if verified.filter(created_at__gte=hour_ago).count() >= settings.VOTE_IP_HOURLY_LIMIT:
        return Ballot.Status.HELD, "ip_burst"
    ten_min_ago = now - timedelta(minutes=10)
    if (
        verified.filter(ua_hash=ua_hash, created_at__gte=ten_min_ago).count()
        >= settings.VOTE_UA_IP_10MIN_LIMIT
    ):
        return Ballot.Status.HELD, "ua_burst"
    return Ballot.Status.COUNTED, ""


# First key of the two-key advisory lock: a fixed namespace, so these locks can never
# collide with another feature's advisory locks.
_VOTE_LOCK_NAMESPACE = 0x766F7465  # "vote"


def _lock_network(ip_hash: str) -> None:
    """Serialise classify-then-insert per client network until the transaction ends
    (security assessment 2026-11-19, YV-35). Without it, parallel ballots from one
    network all counted the same "before" number and all passed the burst limit.
    pg_advisory_xact_lock releases itself at COMMIT/ROLLBACK; the second key is 28 bits
    of the network hash (a rare collision only makes two networks wait for each other)."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_advisory_xact_lock(%s, %s)",
            [_VOTE_LOCK_NAMESPACE, int(ip_hash[:7], 16)],
        )


def cast_ballot(
    *,
    voter_token: str,
    choice_ids: list[int],
    turnstile_ok: bool | None,
    ip: str,
    ua: str,
    asn: int | None = None,
) -> Ballot:
    """Create the ballot + choices atomically. Raises AlreadyVoted on a duplicate
    token (the unique token_hash turns the race into an IntegrityError)."""
    # Validate choices: exact count, all candidate games (docs/voting.md 2b).
    games = list(Game.objects.filter(pk__in=choice_ids, status=Game.Status.CANDIDATE))
    if (
        len(set(choice_ids)) != settings.CHOICES_PER_BALLOT
        or len(games) != settings.CHOICES_PER_BALLOT
    ):
        raise InvalidChoices

    # ip_hash is the HMAC of the client NETWORK (IPv4 address / IPv6 /64), so rotating
    # IPv6 addresses inside one line does not dodge the burst limits (YV-07).
    ip_h, ua_h = network_hash(ip), hmac_hash(ua)
    try:
        with transaction.atomic():
            # Lock, THEN count, THEN insert — all in one transaction (YV-35). Under READ
            # COMMITTED each count sees every ballot committed by an earlier lock holder.
            _lock_network(ip_h)
            status, held_reason = classify(
                turnstile_ok=turnstile_ok, asn=asn, ip_hash=ip_h, ua_hash=ua_h
            )
            ballot = Ballot.objects.create(
                token_hash=token_hash(voter_token),
                status=status,
                held_reason=held_reason,
                turnstile_passed=turnstile_ok is True,
                ip_hash=ip_h,
                ua_hash=ua_h,
                asn=asn,
                signals={"held_reason": held_reason} if held_reason else None,
            )
            BallotChoice.objects.bulk_create(
                BallotChoice(ballot=ballot, game=game) for game in games
            )
    except IntegrityError as exc:
        raise AlreadyVoted from exc
    return ballot


def tally() -> dict:
    """Counted totals per game + held count. Computed, never stored."""
    from django.db.models import Count

    counted = (
        BallotChoice.objects.filter(ballot__status=Ballot.Status.COUNTED)
        .values("game__slug", "game__name_ar")
        .annotate(votes=Count("id"))
        .order_by("-votes")
    )
    return {
        "choices": list(counted),
        "counted": Ballot.objects.filter(status=Ballot.Status.COUNTED).count(),
        "held": Ballot.objects.filter(status=Ballot.Status.HELD).count(),
        "invalidated": Ballot.objects.filter(status=Ballot.Status.INVALIDATED).count(),
    }
