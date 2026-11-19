"""Regression tests for the security assessment of 2026-11-19 (voting):
YV-07 burst limits group IPv6 by /64, YV-34 only verified ballots count toward bursts,
YV-35 classify is serialised per network, YV-39 X-Client-ASN trusted only via Cloudflare."""

import time

import pytest
from django.test import Client, override_settings

from conftest import run_concurrently
from core.models import Game
from voting import services
from voting.models import Ballot
from voting.views import _asn

pytestmark = pytest.mark.django_db


def cast(games, token, ip, turnstile=True, ua="UA", asn=None):
    return services.cast_ballot(
        voter_token=token,
        choice_ids=[g.pk for g in games[:3]],
        turnstile_ok=turnstile,
        ip=ip,
        ua=ua,
        asn=asn,
    )


# --------------------------------------------------------------------------- YV-34


@override_settings(TURNSTILE_ENABLED=True)
def test_unsolved_ballots_do_not_push_real_voters_into_held(
    phase_vote, candidate_games, monkeypatch, settings
):
    """Reviewer PoC test_unsolved_turnstile_ballots_stored_and_poison_network: a few
    token-less POSTs from the campus NAT put every real voter that hour into HELD."""
    ids = [str(g.pk) for g in candidate_games[:3]]
    nat = "198.51.100.9"
    for _ in range(settings.VOTE_IP_HOURLY_LIMIT):
        c = Client()
        c.get("/vote/", REMOTE_ADDR=nat)
        assert c.post("/vote/", {"choices": ids}, REMOTE_ADDR=nat).status_code == 200
    assert Ballot.objects.filter(held_reason="turnstile").count() == settings.VOTE_IP_HOURLY_LIMIT

    monkeypatch.setattr("core.turnstile.verify", lambda token, ip="": token == "solved")
    real = Client()
    real.get("/vote/", REMOTE_ADDR=nat)
    real.post(
        "/vote/",
        {"choices": ids, "cf-turnstile-response": "solved"},
        REMOTE_ADDR=nat,
        HTTP_USER_AGENT="real student",
    )
    ballot = Ballot.objects.order_by("-created_at").first()
    assert ballot.turnstile_passed is True
    assert ballot.status == Ballot.Status.COUNTED


# --------------------------------------------------------------------------- YV-07


@override_settings(VOTE_IP_HOURLY_LIMIT=2, VOTE_UA_IP_10MIN_LIMIT=10)
def test_ipv6_rotation_inside_one_64_hits_the_burst_limit(candidate_games):
    cast(candidate_games, "t1", "2001:db8:1:2::1", ua="a")
    cast(candidate_games, "t2", "2001:db8:1:2::2", ua="b")
    rotated = cast(candidate_games, "t3", "2001:db8:1:2:dead:beef::3", ua="c")
    assert (rotated.status, rotated.held_reason) == (Ballot.Status.HELD, "ip_burst")
    other = cast(candidate_games, "t4", "2001:db8:1:3::1", ua="d")
    assert other.status == Ballot.Status.COUNTED


@override_settings(VOTE_IP_HOURLY_LIMIT=1, VOTE_UA_IP_10MIN_LIMIT=10)
def test_ipv4_mapped_address_is_the_same_network_as_ipv4(candidate_games):
    cast(candidate_games, "t1", "203.0.113.7")
    assert cast(candidate_games, "t2", "::ffff:203.0.113.7").held_reason == "ip_burst"


# --------------------------------------------------------------------------- YV-35


@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
@override_settings(VOTE_IP_HOURLY_LIMIT=2, VOTE_UA_IP_10MIN_LIMIT=100)
def test_parallel_ballots_from_one_network_cannot_all_pass_the_burst_limit(monkeypatch):
    """classify() counted, then the insert happened later with no lock, so a parallel
    wave from one network all saw the same count and all passed. The sleep widens the
    count→insert gap so the race shows every time without the per-network lock."""
    games = [
        Game.objects.create(slug=f"c{i}", name_ar=str(i), status=Game.Status.CANDIDATE)
        for i in range(3)
    ]
    real_classify = services.classify

    def slow_classify(**kwargs):
        result = real_classify(**kwargs)
        time.sleep(0.3)
        return result

    monkeypatch.setattr(services, "classify", slow_classify)
    results = run_concurrently(
        *[lambda i=i: cast(games, f"tok-{i}", "198.51.100.77", ua=f"ua{i}") for i in range(6)]
    )
    assert [exc for _, exc in results] == [None] * 6
    assert Ballot.objects.filter(status=Ballot.Status.COUNTED).count() == 2
    assert Ballot.objects.filter(held_reason="ip_burst").count() == 4


# --------------------------------------------------------------------------- YV-39


def test_asn_header_is_ignored_without_the_origin_shield(rf):
    """Reviewer PoC test_asn_header_is_client_controlled."""
    assert _asn(rf.post("/vote/", HTTP_X_CLIENT_ASN="25019")) is None


@override_settings(CF_ORIGIN_TOKEN="shield")
def test_asn_header_is_ignored_without_a_valid_origin_token(rf):
    assert _asn(rf.post("/vote/", HTTP_X_CLIENT_ASN="25019")) is None
    assert _asn(rf.post("/vote/", HTTP_X_CLIENT_ASN="25019", HTTP_X_ORIGIN_TOKEN="nope")) is None


@override_settings(CF_ORIGIN_TOKEN="shield")
@pytest.mark.parametrize(
    "value, expected",
    [
        ("25019", 25019),
        ("4200000000", 4200000000),  # 32-bit private-use ASN
        ("4294967296", None),  # out of range
        ("0", None),
        ("-5", None),
        ("AS25019", None),
        ("٢٥٠١٩", None),  # not ASCII
        ("", None),
    ],
)
def test_asn_header_is_trusted_through_cloudflare_and_range_checked(rf, value, expected):
    request = rf.post("/vote/", HTTP_X_CLIENT_ASN=value, HTTP_X_ORIGIN_TOKEN="shield")
    assert _asn(request) == expected


def test_32_bit_asn_can_be_stored(candidate_games):
    ballot = cast(candidate_games, "t1", "203.0.113.7", asn=4200000000)
    ballot.refresh_from_db()
    assert ballot.asn == 4200000000
