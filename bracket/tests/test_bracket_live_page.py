"""Public bracket page (/bracket/<slug>/) + live polling hooks. The polling script
(static/js/bracket-live.js) finds cells by data-match="<round>-<slot>", so the page
and the JSON must agree on those keys; the page must stay complete without JS."""

import re

import pytest
from django.contrib.auth.models import User

from bracket import services
from bracket.draw import draw
from bracket.models import Match
from conftest import fill_confirmed
from core.content import CONTENT

pytestmark = pytest.mark.django_db


@pytest.fixture
def drawn(game, phase_event):
    fill_confirmed(game, 16)
    draw(game, seed=1)
    return game


def test_page_carries_live_hooks_and_arabic_labels(client, drawn):
    body = client.get(f"/bracket/{drawn.slug}/").content.decode()
    assert f'data-api="/api/bracket/{drawn.slug}.json"' in body
    assert f'data-pending="{CONTENT["MATCH_PENDING"]}"' in body
    assert "js/bracket-live.js" in body
    assert body.count('class="match-cell"') == 15


def test_cells_are_in_round_then_slot_order_and_match_the_api_keys(client, drawn):
    body = client.get(f"/bracket/{drawn.slug}/").content.decode()
    page_keys = re.findall(r'data-match="(\d+-\d+)"', body)
    api = client.get(f"/api/bracket/{drawn.slug}.json").json()["matches"]
    api_keys = [f"{m['round']}-{m['slot']}" for m in api]
    assert page_keys == api_keys
    assert page_keys[:3] == ["1-1", "1-2", "1-3"] and page_keys[-1] == "4-1"


def test_champion_panel_hidden_until_the_final_is_won(client, drawn):
    body = client.get(f"/bracket/{drawn.slug}/").content.decode()
    assert re.search(r"data-champion[^>]*hidden", body)

    referee = User.objects.create_user("ref", password="x", is_staff=True)
    for round_ in (1, 2, 3, 4):
        for m in Match.objects.filter(game=drawn, round=round_).order_by("slot"):
            services.enter_result(m, m.player1, "1–0", actor=referee)
    final = Match.objects.get(game=drawn, round=4)

    body = client.get(f"/bracket/{drawn.slug}/").content.decode()
    assert not re.search(r"data-champion[^>]*hidden", body)
    assert final.winner.game_player_id in body


def test_page_is_edge_cacheable(client, drawn):
    response = client.get(f"/bracket/{drawn.slug}/")
    assert "Set-Cookie" not in response.headers
    assert "max-age=30" in response["Cache-Control"]
