"""Voting critical tests (docs/testing.md → Voting)."""

import pytest
from django.test import override_settings

from conftest import set_phase
from core.models import AuditLog, Game
from core.phases import Phase
from voting import services
from voting.models import Ballot

pytestmark = pytest.mark.django_db

IP = "203.0.113.7"
UA = "Mozilla/5.0 test"


def cast(games, token="tok-1", turnstile=True, ip=IP, ua=UA, asn=None):
    return services.cast_ballot(
        voter_token=token,
        choice_ids=[g.pk for g in games[:3]],
        turnstile_ok=turnstile,
        ip=ip,
        ua=ua,
        asn=asn,
    )


def test_one_ballot_per_token(candidate_games):
    cast(candidate_games, token="tok-x")
    with pytest.raises(services.AlreadyVoted):
        cast(candidate_games, token="tok-x")
    assert Ballot.objects.count() == 1


def test_ballot_choice_count_enforced(candidate_games):
    with pytest.raises(services.InvalidChoices):
        services.cast_ballot(
            voter_token="t", choice_ids=[candidate_games[0].pk], turnstile_ok=True, ip=IP, ua=UA
        )
    with pytest.raises(services.InvalidChoices):
        services.cast_ballot(
            voter_token="t",
            choice_ids=[g.pk for g in candidate_games[:4]],
            turnstile_ok=True,
            ip=IP,
            ua=UA,
        )
    assert Ballot.objects.count() == 0


def test_choice_must_be_candidate_game(candidate_games):
    confirmed = Game.objects.create(slug="conf", name_ar="x", status=Game.Status.CONFIRMED)
    with pytest.raises(services.InvalidChoices):
        services.cast_ballot(
            voter_token="t",
            choice_ids=[candidate_games[0].pk, candidate_games[1].pk, confirmed.pk],
            turnstile_ok=True,
            ip=IP,
            ua=UA,
        )


def test_turnstile_fail_goes_to_held(candidate_games):
    ballot = cast(candidate_games, token="t1", turnstile=False)
    assert ballot.status == Ballot.Status.HELD
    assert ballot.held_reason == "turnstile"
    # Unreachable (None) is also held, never rejected.
    ballot2 = cast(candidate_games, token="t2", turnstile=None)
    assert ballot2.status == Ballot.Status.HELD


def test_datacenter_asn_held(candidate_games):
    ballot = cast(candidate_games, token="t1", asn=16509)  # AWS
    assert ballot.status == Ballot.Status.HELD
    assert ballot.held_reason == "datacenter"


@override_settings(VOTE_UA_IP_10MIN_LIMIT=100)  # isolate the IP rule
def test_ip_burst_held(candidate_games):
    for i in range(5):
        b = cast(candidate_games, token=f"t{i}", ua=f"ua-{i}")
        assert b.status == Ballot.Status.COUNTED
    sixth = cast(candidate_games, token="t-6", ua="ua-6")
    assert sixth.status == Ballot.Status.HELD
    assert sixth.held_reason == "ip_burst"


def test_ua_ip_burst_held(candidate_games):
    for i in range(3):
        b = cast(candidate_games, token=f"t{i}")
        assert b.status == Ballot.Status.COUNTED
    fourth = cast(candidate_games, token="t-4")
    assert fourth.status == Ballot.Status.HELD
    assert fourth.held_reason == "ua_burst"


def test_no_raw_ip_stored(candidate_games):
    cast(candidate_games, token="t1")
    ballot = Ballot.objects.get()
    for field in ("token_hash", "ip_hash", "ua_hash", "held_reason"):
        assert IP not in (getattr(ballot, field) or "")
        assert UA not in (getattr(ballot, field) or "")
    assert IP not in str(ballot.signals)


def test_vote_phase_gate(client, candidate_games):
    """POST outside the window -> 403, no row, even with a valid cookie."""
    set_phase(Phase.VOTE)
    client.get("/vote/")  # obtain the voter cookie while the window is open
    set_phase(Phase.PRE)
    assert (
        client.post("/vote/", {"choices": [g.pk for g in candidate_games[:3]]}).status_code == 403
    )
    set_phase(Phase.PERMITS)
    assert (
        client.post("/vote/", {"choices": [g.pk for g in candidate_games[:3]]}).status_code == 403
    )
    assert Ballot.objects.count() == 0


def test_vote_view_end_to_end(client, phase_vote, candidate_games):
    """GET issues the cookie; POST creates a counted ballot (Turnstile disabled
    in tests = treated as passed); duplicate POST shows the already-voted page."""
    client.get("/vote/")
    response = client.post("/vote/", {"choices": [g.pk for g in candidate_games[:3]]})
    assert response.status_code == 200
    assert Ballot.objects.filter(status=Ballot.Status.COUNTED).count() == 1
    response = client.post("/vote/", {"choices": [g.pk for g in candidate_games[:3]]})
    assert Ballot.objects.count() == 1  # AlreadyVoted path


def test_tally_hidden_during_vote(client, phase_vote, candidate_games):
    assert b"<table>" not in client.get("/vote/results/").content


def test_bulk_invalidate_audited(admin_user, candidate_games):
    from django.contrib.admin.sites import site

    from voting.admin import BallotAdmin
    from voting.models import Ballot as B

    for i in range(3):
        cast(candidate_games, token=f"t{i}", ua=f"ua-{i}", ip=f"198.51.100.{i}")
    model_admin = BallotAdmin(B, site)

    class Req:
        user = admin_user

    model_admin.mark_invalidated(Req(), B.objects.all())
    assert B.objects.filter(status=B.Status.INVALIDATED).count() == 3
    logs = AuditLog.objects.filter(action="ballot.invalidate")
    assert logs.count() == 3
    assert all(log.actor == admin_user for log in logs)
