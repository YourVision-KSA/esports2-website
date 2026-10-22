"""Layout of the public bracket page: a mirrored single-elimination tree.

Pure presentation logic (no queries, no writes) so it is easy to read and to test.

    visual (RTL page):   [R16 1-4] [QF 1-2] [SF 1]  FINAL  [SF 2] [QF 3-4] [R16 5-8]
                          start side ───────────────▶ ◀─────────────── end side

Each match gets a public number like the printed bracket sheets: round of 16 = 1..8,
quarter-finals = 9..12, semi-finals = 13..14, final = 15 (offset by round + slot).
Empty slots show who feeds them ("winner of M3"), found through next_match/next_slot.
"""

from dataclasses import dataclass, field

from core.content import CONTENT

from .models import Match

FINAL_ROUND = 4
_OFFSET = {1: 0, 2: 8, 3: 12, 4: 14}  # match number = offset[round] + slot
_SLOTS = {1: 8, 2: 4, 3: 2, 4: 1}  # matches per round in a 16-player bracket


def match_number(round_: int, slot: int) -> int:
    return _OFFSET[round_] + slot


@dataclass
class Cell:
    match: Match
    number: int
    label: str  # "م3"
    placeholder1: str  # shown while player1 is unknown ("فائز م1" or "—")
    placeholder2: str

    @property
    def key(self) -> str:
        return f"{self.match.round}-{self.match.slot}"


@dataclass
class Column:
    round: int
    side: str  # "start" | "end" | "center"
    title: str
    day: str
    groups: list[list[Cell]] = field(default_factory=list)  # pairs feeding one next match


def build(matches: list[Match]) -> list[Column]:
    """Arrange a game's matches into the 7 mirrored columns (start side → final → end side)."""
    by_key = {(m.round, m.slot): m for m in matches}
    feeders = {(m.next_match_id, m.next_slot): m for m in matches if m.next_match_id}

    def cell(m: Match) -> Cell:
        def ph(slot: int) -> str:
            src = feeders.get((m.pk, slot))
            if src is None:
                return "—"
            n = match_number(src.round, src.slot)
            return CONTENT["WINNER_OF"].replace("{n}", str(n))

        n = match_number(m.round, m.slot)
        return Cell(m, n, CONTENT["MATCH_NO"].replace("{n}", str(n)), ph(1), ph(2))

    def column(round_: int, side: str, slots: range) -> Column:
        cells = [cell(by_key[(round_, s)]) for s in slots if (round_, s) in by_key]
        pairs = (
            [cells[i : i + 2] for i in range(0, len(cells), 2)]
            if round_ < 3
            else [[c] for c in cells]
        )
        return Column(
            round_,
            side,
            CONTENT["ROUND_NAMES"].get(round_, f"R{round_}"),
            CONTENT["ROUND_DAYS"].get(round_, ""),
            pairs,
        )

    half = {r: _SLOTS[r] // 2 for r in (1, 2, 3)}
    start = [column(r, "start", range(1, half[r] + 1)) for r in (1, 2, 3)]
    end = [column(r, "end", range(half[r] + 1, _SLOTS[r] + 1)) for r in (3, 2, 1)]
    final = column(FINAL_ROUND, "center", range(1, 2))
    return [*start, final, *end]
