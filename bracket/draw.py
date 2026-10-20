"""Bracket draw (docs/data-model.md): random, seedable, logged. Builds the full
single-elimination tree (R16→final) and feeds R1 from confirmed registrations.
Byes (fewer than 16 players) become forfeit wins that propagate immediately."""

import random

from django.db import transaction

from core import audit
from core.models import Game
from registration.models import Registration

from .models import Match
from .services import _propagate

ROUNDS = {1: 8, 2: 4, 3: 2, 4: 1}  # round -> number of matches


@transaction.atomic
def draw(game: Game, seed: int | None = None, actor=None) -> list[Match]:
    """Create the 15-match tree for `game`. Refuses if matches already exist."""
    if game.matches.exists():
        raise ValueError(f"{game.slug}: bracket already drawn")

    players = list(
        Registration.objects.filter(game=game, status=Registration.Status.CONFIRMED).order_by("id")
    )
    if not 2 <= len(players) <= game.seats:
        raise ValueError(
            f"{game.slug}: need 2..{game.seats} confirmed players, have {len(players)}"
        )

    rng = random.Random(seed)
    rng.shuffle(players)

    # Build the tree from the final backwards so next_match links exist.
    by_round: dict[int, list[Match]] = {}
    for rnd in sorted(ROUNDS, reverse=True):
        by_round[rnd] = [
            Match.objects.create(game=game, round=rnd, slot=slot)
            for slot in range(1, ROUNDS[rnd] + 1)
        ]
    for rnd in (1, 2, 3):
        for match in by_round[rnd]:
            match.next_match = by_round[rnd + 1][(match.slot - 1) // 2]
            match.next_slot = 1 if match.slot % 2 == 1 else 2
            match.save(update_fields=["next_match", "next_slot"])

    # Feed round 1 by dealing players round-robin across the 8 matches, so byes
    # (missing opponents) spread over distinct matches instead of stacking into
    # one empty match: a lone player gets a forfeit win that propagates.
    p1_seats: list = [None] * 8
    p2_seats: list = [None] * 8
    for idx, player in enumerate(players):
        if idx < 8:
            p1_seats[idx] = player
        else:
            p2_seats[idx - 8] = player
    for match in by_round[1]:
        p1 = p1_seats[match.slot - 1]
        p2 = p2_seats[match.slot - 1]
        match.player1, match.player2 = p1, p2
        if p1 and not p2:
            match.winner, match.status = p1, Match.Status.FORFEIT
        elif p2 and not p1:
            match.winner, match.status = p2, Match.Status.FORFEIT
        match.save()
        if match.winner:
            _propagate(match, match.winner)

    audit.record(
        actor,
        "bracket.draw",
        model="core.Game",
        object_id=game.slug,
        after={"seed": seed, "players": len(players)},
    )
    return [m for matches in by_round.values() for m in matches]
