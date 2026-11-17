"""Production settings fail CLOSED (audit 2026-11-13, finding 3).

Each case imports esports.settings.production in a fresh Python process with a fully
controlled environment (the settings run at import time, so this cannot be done with
override_settings). Every variable is set explicitly — base.py's read_env() only fills
variables that are NOT set, so the developer's .env cannot leak into these cases.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

GOOD = {
    "SECRET_KEY": "prod-secret",
    "SIGNALS_SALT": "prod-salt",
    "TURNSTILE_SECRET": "0x4AAAAAAA-real-secret",
    "TURNSTILE_SITE_KEY": "0x4AAAAAAA-real-site-key",
    "TURNSTILE_ENABLED": "True",
    "INTERNAL_TOKEN": "prod-internal",
    "SITE_BASE_URL": "https://esports.example.sa",
    "CF_ORIGIN_TOKEN": "shield-secret",
    "ALLOW_NO_ORIGIN_SHIELD": "False",
    "ALLOWED_HOSTS": "esports.example.sa",
    "DATABASE_URL": "postgres://u:p@127.0.0.1:5432/x",
}

PROBE = (
    "import json, django; from django.conf import settings; django.setup(); "
    "print(json.dumps({k: getattr(settings, k) for k in "
    "('TURNSTILE_ENABLED', 'SITE_BASE_URL', 'CF_ORIGIN_TOKEN', 'REQUIRE_2FA', 'MIDDLEWARE', "
    "'CSRF_COOKIE_HTTPONLY', 'SESSION_COOKIE_SECURE', 'CSRF_COOKIE_SECURE')}))"
)


def load(**overrides):
    env = {
        "PATH": os.environ.get("PATH", ""),
        "DJANGO_SETTINGS_MODULE": "esports.settings.production",
        **GOOD,
        **overrides,
    }
    return subprocess.run(
        [sys.executable, "-c", PROBE], cwd=ROOT, env=env, capture_output=True, text=True
    )


def test_complete_production_config_starts():
    result = load()
    assert result.returncode == 0, result.stderr
    values = json.loads(result.stdout)
    assert values["TURNSTILE_ENABLED"] is True
    assert values["SITE_BASE_URL"] == "https://esports.example.sa"
    assert values["REQUIRE_2FA"] is True
    assert values["CSRF_COOKIE_HTTPONLY"] is values["SESSION_COOKIE_SECURE"] is True
    assert values["CSRF_COOKIE_SECURE"] is True
    # First, so responses returned by any other middleware carry the CSP too.
    assert values["MIDDLEWARE"][0] == "core.middleware.SecurityHeadersMiddleware"


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"CF_ORIGIN_TOKEN": ""}, "CF_ORIGIN_TOKEN is not set"),
        ({"TURNSTILE_ENABLED": "False"}, "TURNSTILE_ENABLED must not be False"),
        ({"TURNSTILE_SITE_KEY": ""}, "TURNSTILE_SITE_KEY is not set"),
        ({"TURNSTILE_SITE_KEY": "1x00000000000000000000AA"}, "test key"),
        ({"TURNSTILE_SECRET": "1x0000000000000000000000000000000AA"}, "test key"),
        ({"SITE_BASE_URL": ""}, "SITE_BASE_URL is not set"),
        ({"SITE_BASE_URL": "http://esports.example.sa"}, "SITE_BASE_URL must be"),
        ({"SITE_BASE_URL": "https://127.0.0.1:8000"}, "SITE_BASE_URL must be"),
        ({"SECRET_KEY": ""}, "SECRET_KEY is not set"),
        ({"SECRET_KEY": "dev-only-change-me"}, "dev default"),
        ({"SIGNALS_SALT": "dev-only-salt"}, "dev default"),
    ],
)
def test_misconfigured_production_refuses_to_start(overrides, message):
    result = load(**overrides)
    assert result.returncode != 0
    assert "Production misconfiguration" in result.stderr and message in result.stderr


def test_staging_without_cloudflare_must_opt_out_explicitly():
    result = load(CF_ORIGIN_TOKEN="", ALLOW_NO_ORIGIN_SHIELD="True")
    assert result.returncode == 0, result.stderr


def test_csp_header_added_unless_already_present(rf):
    from django.http import HttpResponse

    from core.middleware import CONTENT_SECURITY_POLICY, SecurityHeadersMiddleware

    response = SecurityHeadersMiddleware(lambda request: HttpResponse())(rf.get("/"))
    assert response["Content-Security-Policy"] == CONTENT_SECURITY_POLICY
    assert "frame-ancestors 'none'" in CONTENT_SECURITY_POLICY
    assert "https://challenges.cloudflare.com" in CONTENT_SECURITY_POLICY  # Turnstile

    def preset(request):
        r = HttpResponse()
        r["Content-Security-Policy"] = "default-src 'none'"
        return r

    assert (
        SecurityHeadersMiddleware(preset)(rf.get("/"))["Content-Security-Policy"]
        == "default-src 'none'"
    )


def _directives(policy: str) -> dict[str, list[str]]:
    return {part.split()[0]: part.split()[1:] for part in policy.split(";") if part.strip()}


def test_csp_allows_what_the_3d_hero_needs():
    """Pre-merge review: the hero scene loads a meshopt-compressed .glb. The decoder is
    WebAssembly ('wasm-unsafe-eval'), and the model's embedded textures reach the browser
    as blob: URLs (fetched → connect-src, decoded as images → img-src). Without these the
    scene silently falls back to the poster for every visitor."""
    from core.middleware import CONTENT_SECURITY_POLICY

    csp = _directives(CONTENT_SECURITY_POLICY)
    assert "'wasm-unsafe-eval'" in csp["script-src"]
    assert "blob:" in csp["connect-src"]
    assert "blob:" in csp["img-src"]
    # ...and nothing broader than that
    assert "'unsafe-eval'" not in csp["script-src"]
    assert "'unsafe-inline'" not in csp["script-src"]


def test_documented_edge_rule_matches_the_app_policy():
    """docs/operations.md tells staff which CSP to paste into the Cloudflare rule; the
    edge rule overrides the app's header, so the two must not drift apart."""
    import re
    from pathlib import Path

    from core.middleware import CONTENT_SECURITY_POLICY

    doc = (Path(__file__).resolve().parents[2] / "docs" / "operations.md").read_text()
    documented = re.search(r"`Content-Security-Policy: ([^`]+)`", doc).group(1)
    assert _directives(documented) == _directives(CONTENT_SECURITY_POLICY)


@pytest.fixture
def production_middleware(settings):
    """The same order production.py builds: the CSP middleware in front of base's list."""
    settings.MIDDLEWARE = ["core.middleware.SecurityHeadersMiddleware", *settings.MIDDLEWARE]


@pytest.mark.django_db
def test_responses_from_earlier_middleware_carry_the_csp(production_middleware, settings):
    from django.test import Client

    from core.middleware import CONTENT_SECURITY_POLICY

    # the https redirect (SecurityMiddleware)
    settings.SECURE_SSL_REDIRECT = True
    redirect = Client().get("/")
    assert redirect.status_code == 301
    assert redirect["Content-Security-Policy"] == CONTENT_SECURITY_POLICY
    settings.SECURE_SSL_REDIRECT = False

    # the origin-shield 403 (CloudflareOriginMiddleware)
    settings.CF_ORIGIN_TOKEN = "shield"
    blocked = Client().get("/")
    assert blocked.status_code == 403
    assert blocked["Content-Security-Policy"] == CONTENT_SECURITY_POLICY
    settings.CF_ORIGIN_TOKEN = ""

    # the CSRF failure page (CsrfViewMiddleware)
    csrf = Client(enforce_csrf_checks=True).post("/staff/login/", {"username": "x"})
    assert csrf.status_code == 403
    assert csrf["Content-Security-Policy"] == CONTENT_SECURITY_POLICY
