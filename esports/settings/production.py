"""
Production settings (Cloud Run + Cloud SQL, me-central2 — docs/operations.md).

Every value here that differs from base is a hardening step; do not relax them.
Misconfiguration fails CLOSED: the app refuses to start (tested in a subprocess by
core/tests/test_production_settings.py).
"""

from .base import *  # noqa: F401,F403
from .base import MIDDLEWARE, env

DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")  # required, no default

# Behind Cloudflare + Cloud Run: both terminate TLS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# No site JavaScript reads the CSRF cookie (forms carry the token), so hide it from scripts.
CSRF_COOKIE_HTTPONLY = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
# 30 days until the final domain is fixed (DEC-04); raise to 1 year (31536000) then.
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# Content-Security-Policy from the app as well as from the Cloudflare Transform Rule
# (docs/operations.md → Cloudflare checklist step 6), so a missing edge rule or a request
# that reaches the origin some other way is still covered (audit 2026-11-13).
MIDDLEWARE = [*MIDDLEWARE, "core.middleware.SecurityHeadersMiddleware"]

# Sessions exist only for staff (public pages set no cookies — CLAUDE.md rule 8).
# 12 h instead of Django's 2-week default limits a stolen admin session's lifetime.
SESSION_COOKIE_AGE = 60 * 60 * 12

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# 2FA is mandatory for staff in production (CLAUDE.md hard rule 4).
REQUIRE_2FA = True


# ---------------------------------------------------------------------------------------
# Fail fast if production is misconfigured.
# ---------------------------------------------------------------------------------------
def _fail(message: str):
    raise RuntimeError(f"Production misconfiguration: {message}")


for _name in (
    "SECRET_KEY",
    "SIGNALS_SALT",
    "TURNSTILE_SECRET",
    "TURNSTILE_SITE_KEY",
    "INTERNAL_TOKEN",
    "SITE_BASE_URL",
):
    if not env(_name, default=""):
        _fail(f"{_name} is not set")
if env("SECRET_KEY") == "dev-only-change-me":
    _fail("SECRET_KEY is the dev default")
if env("SIGNALS_SALT") == "dev-only-salt":
    _fail("SIGNALS_SALT is the dev default")

# Turnstile: the bot check on the vote AND on registration. "False" in production would
# silently wave every request through (core/turnstile.py), so it is not an option here.
if not env.bool("TURNSTILE_ENABLED", default=True):
    _fail("TURNSTILE_ENABLED must not be False")
TURNSTILE_ENABLED = True
# Cloudflare's documented test keys always pass (or always fail) — never in production.
if env("TURNSTILE_SITE_KEY").startswith(("1x0000", "2x0000", "3x0000")):
    _fail("TURNSTILE_SITE_KEY is a Cloudflare test key")
if env("TURNSTILE_SECRET").startswith(("1x0000", "2x0000", "3x0000")):
    _fail("TURNSTILE_SECRET is a Cloudflare test key")

# Absolute links in emails and VIP QR codes. Must be the public https origin, no path.
SITE_BASE_URL = env("SITE_BASE_URL").rstrip("/")
if not SITE_BASE_URL.startswith("https://") or "127.0.0.1" in SITE_BASE_URL:
    _fail("SITE_BASE_URL must be the public https:// origin (e.g. https://example.sa)")

# Origin shield (core/middleware.py). Without it the *.run.app URL skips Cloudflare's rate
# rules and client_ip() falls back to the socket address. A deployment that is knowingly
# not behind Cloudflare (e.g. a staging service) must say so explicitly.
CF_ORIGIN_TOKEN = env("CF_ORIGIN_TOKEN", default="")
if not CF_ORIGIN_TOKEN and not env.bool("ALLOW_NO_ORIGIN_SHIELD", default=False):
    _fail("CF_ORIGIN_TOKEN is not set (set ALLOW_NO_ORIGIN_SHIELD=True only for staging)")
