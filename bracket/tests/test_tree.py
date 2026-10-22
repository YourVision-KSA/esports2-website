"""bracket/tree.py — numbering, mirroring and feeder placeholders (no HTTP)."""

import pytest

from bracket import tree
from bracket.draw import draw
from conftest import fill_confirmed
from core.content import CONTENT

pytestmark = pytest.mark.django_db


def test_match_numbers_follow_the_printed_sheet():
    assert [tree.match_number(1, s) for s in (1, 8)] == [1, 8]
    assert [tree.match_number(2, s) for s in (1, 4)] == [9, 12]
    assert [tree.match_number(3, s) for s in (1, 2)] == [13, 14]
    assert tree.match_number(4, 1) == 15


def test_columns_mirror_around_the_final(game):
    fill_confirmed(game, 16)
    matches = list(draw(game, seed=3))
    cols = tree.build(matches)
    assert [(c.round, c.side) for c in cols] == [
        (1, "start"), (2, "start"), (3, "start"), (4, "center"),
        (3, "end"), (2, "end"), (1, "end"),
    ]  # fmt: skip
    # R16 halves are two pairs each; QF halves one pair; SF and final are singles
    assert [len(c.groups) for c in cols] == [2, 1, 1, 1, 1, 1, 2]
    assert [len(g) for g in cols[0].groups] == [2, 2]
    assert cols[0].day == CONTENT["ROUND_DAYS"][1]


def test_placeholders_point_at_the_feeding_matches(game):
    fill_confirmed(game, 16)
    columns = tree.build(list(draw(game, seed=3)))
    cells = {c.key: c for col in columns for g in col.groups for c in g}
    winner_of = CONTENT["WINNER_OF"]
    assert cells["2-1"].placeholder1 == winner_of.replace("{n}", "1")
    assert cells["2-1"].placeholder2 == winner_of.replace("{n}", "2")
    assert cells["4-1"].placeholder2 == winner_of.replace("{n}", "14")
    assert cells["1-1"].placeholder1 == "—"  # first round has no feeder
