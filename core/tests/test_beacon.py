"""Count-only 3D tier beacon (core/beacon.py, POST /beacon/3d)."""

import pytest
from django.core.management import call_command
from django.test import Client

from conftest import run_concurrently
from core.beacon import record_tier
from core.models import TierStat

pytestmark = pytest.mark.django_db

FORM = "application/x-www-form-urlencoded"  # what navigator.sendBeacon sends


def _post(client, body):
    return client.post("/beacon/3d", body, content_type=FORM)


def test_beacon_counts_per_day_outcome_and_device(client):
    assert _post(client, "o=mid&d=mobile").status_code == 204
    assert _post(client, "o=mid&d=mobile").status_code == 204
    assert _post(client, "o=fallback&d=mobile").status_code == 204
    counts = {(s.outcome, s.device): s.count for s in TierStat.objects.all()}
    assert counts == {("mid", "mobile"): 2, ("fallback", "mobile"): 1}


@pytest.mark.parametrize("body", ["o=ultra&d=mobile", "o=mid&d=fridge", "", "o=mid"])
def test_unknown_values_are_rejected_and_not_stored(client, body):
    assert _post(client, body).status_code == 400
    assert not TierStat.objects.exists()


def test_only_post_and_small_bodies(client):
    assert client.get("/beacon/3d").status_code == 405
    assert _post(client, "o=mid&d=mobile&pad=" + "x" * 300).status_code == 413


def test_works_without_csrf_token_and_sets_no_cookie():
    """Fired from the edge-cached home page, which has no CSRF token (rule 8)."""
    response = _post(Client(enforce_csrf_checks=True), "o=high&d=desktop")
    assert response.status_code == 204
    assert "Set-Cookie" not in response.headers


def test_nothing_identifying_is_stored():
    fields = {f.name for f in TierStat._meta.get_fields()}
    assert fields == {"id", "day", "outcome", "device", "count"}


@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
def test_simultaneous_first_beacons_of_the_day_both_count():
    """Two inserts racing for the same new (day, outcome, device) row: no lost count."""
    results = run_concurrently(
        lambda: record_tier("high", "desktop"), lambda: record_tier("high", "desktop")
    )
    assert [exc for _, exc in results] == [None, None]
    assert TierStat.objects.get(outcome="high", device="desktop").count == 2


def test_tier_report_shows_fallback_share(capsys):
    for _ in range(3):
        record_tier("mid", "mobile")
    record_tier("fallback", "mobile")
    call_command("tier_report")
    out = capsys.readouterr().out
    assert "mobile" in out and "25.0%" in out
