"""Origin shield (core/middleware.py — security review 2026-10-22, finding M1).

When CF_ORIGIN_TOKEN is set, only requests carrying the header a Cloudflare Transform
Rule adds may reach the app; direct hits on the Cloud Run URL get 403. /healthz (uptime
checks, deploy smoke test) and /internal/ (Cloud Scheduler, own token auth) stay open.
client_ip() must only trust CF-Connecting-IP while that shield is active.
"""

import pytest
from django.test import override_settings

from core.security import client_ip

pytestmark = pytest.mark.django_db


def test_disabled_by_default_in_development(client):
    assert client.get("/").status_code == 200


@override_settings(CF_ORIGIN_TOKEN="shield-secret")
def test_direct_origin_hits_are_rejected(client):
    assert client.get("/").status_code == 403


@override_settings(CF_ORIGIN_TOKEN="shield-secret")
def test_wrong_token_is_rejected(client):
    assert client.get("/", HTTP_X_ORIGIN_TOKEN="guess").status_code == 403


@override_settings(CF_ORIGIN_TOKEN="shield-secret")
def test_requests_through_cloudflare_pass(client):
    assert client.get("/", HTTP_X_ORIGIN_TOKEN="shield-secret").status_code == 200


@override_settings(CF_ORIGIN_TOKEN="shield-secret")
def test_healthz_stays_reachable_for_uptime_checks(client):
    assert client.get("/healthz").status_code == 200


@override_settings(CF_ORIGIN_TOKEN="shield-secret", INTERNAL_TOKEN="tick-secret")
def test_scheduler_endpoint_stays_reachable_with_its_own_auth(client):
    response = client.post("/internal/outbox/", HTTP_X_INTERNAL_TOKEN="tick-secret")
    assert response.status_code == 200


@override_settings(CF_ORIGIN_TOKEN="shield-secret", INTERNAL_TOKEN="tick-secret")
def test_scheduler_endpoint_still_requires_its_own_token(client):
    assert client.post("/internal/outbox/").status_code == 403


def test_client_ip_ignores_cf_header_without_the_shield(rf):
    """Direct-to-origin requests could spoof CF-Connecting-IP to evade the vote's
    per-IP burst detection — so without the shield, only the socket address counts."""
    request = rf.get("/", HTTP_CF_CONNECTING_IP="203.0.113.9", REMOTE_ADDR="198.51.100.4")
    assert client_ip(request) == "198.51.100.4"


@override_settings(CF_ORIGIN_TOKEN="shield-secret")
def test_client_ip_trusts_cf_header_behind_the_shield(rf):
    request = rf.get("/", HTTP_CF_CONNECTING_IP="203.0.113.9", REMOTE_ADDR="198.51.100.4")
    assert client_ip(request) == "203.0.113.9"
