"""Referee results page (/staff/results/): the phone UI over services.enter_result.
The transaction itself is covered in test_bracket.py; these tests cover the page."""

import pytest
from django.contrib.auth.models import Group, User
from django.core.management import call_command

from bracket.draw import draw
from bracket.models import Match
from conftest import fill_confirmed
from core.content import CONTENT

pytestmark = pytest.mark.django_db


@pytest.fixture
def referee_client(client, game):
    call_command("setup_roles")
    user = User.objects.create_user("ref1", password="x", is_staff=True)
    user.groups.add(Group.objects.get(name="referee"))
    client.login(username="ref1", password="x")
    fill_confirmed(game, 16)
    draw(game, seed=1)
    return client


def _first_match(game):
    return Match.objects.filter(game=game, round=1).order_by("slot").first()


def test_lists_playable_matches_with_arabic_round_names(referee_client, game):
    body = referee_client.get("/staff/results/").content.decode()
    assert CONTENT["ROUND_NAMES"][1] in body
    assert CONTENT["STAFF_SAVE_RESULT"] in body
    assert CONTENT["REG_SUBMIT"] not in body  # the old, wrong button label
    assert body.count('class="match-entry"') == 8  # round of 16


def test_save_result_redirects_with_confirmation(referee_client, game):
    match = _first_match(game)
    response = referee_client.post(
        "/staff/results/",
        {"match_id": match.pk, "winner_id": match.player2_id, "score": "3–1"},
        follow=True,
    )
    match.refresh_from_db()
    assert match.status == Match.Status.DONE and match.winner_id == match.player2_id
    assert match.score_text == "3–1"
    saved = CONTENT["STAFF_RESULT_SAVED"].replace("{winner}", match.player2.game_player_id)
    assert saved in response.content.decode()
    assert response.redirect_chain[-1][0] == "/staff/results/"  # POST/redirect/GET


def test_missing_winner_changes_nothing(referee_client, game):
    match = _first_match(game)
    response = referee_client.post("/staff/results/", {"match_id": match.pk}, follow=True)
    match.refresh_from_db()
    assert match.status == Match.Status.PENDING
    assert CONTENT["STAFF_ERR_WINNER"] in response.content.decode()


def test_second_phone_entering_same_match_gets_arabic_error(referee_client, game):
    match = _first_match(game)
    data = {"match_id": match.pk, "winner_id": match.player1_id}
    referee_client.post("/staff/results/", data)
    response = referee_client.post("/staff/results/", data, follow=True)
    assert CONTENT["STAFF_ERR_SAVE"] in response.content.decode()
    match.refresh_from_db()
    assert match.winner_id == match.player1_id  # first entry kept


def test_game_filter_is_kept_after_saving(referee_client, game):
    match = _first_match(game)
    response = referee_client.post(
        f"/staff/results/?game={game.slug}",
        {"match_id": match.pk, "winner_id": match.player1_id, "game": game.slug},
    )
    assert response.status_code == 302
    assert response["Location"] == f"/staff/results/?game={game.slug}"


def test_staff_page_has_logout_and_no_cache(referee_client):
    response = referee_client.get("/staff/results/")
    assert 'action="/staff/logout/"' in response.content.decode()
    assert "no-cache" in response["Cache-Control"] or "no-store" in response["Cache-Control"]
