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
    assert "core.middleware.SecurityHeadersMiddleware" in values["MIDDLEWARE"]


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
