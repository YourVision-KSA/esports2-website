"""
Production settings (Cloud Run + Cloud SQL, me-central2 — docs/operations.md).

Every value here that differs from base is a hardening step; do not relax them.
"""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")  # required, no default

# Behind Cloudflare + Cloud Run: both terminate TLS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# 2FA is mandatory for staff in production (CLAUDE.md hard rule 4).
REQUIRE_2FA = True

# Fail fast if production is misconfigured.
for _name in ("SECRET_KEY", "SIGNALS_SALT", "TURNSTILE_SECRET", "INTERNAL_TOKEN"):
    if not env(_name, default=""):
        raise RuntimeError(f"Production misconfiguration: {_name} is not set")
if env("SECRET_KEY") == "dev-only-change-me":
    raise RuntimeError("Production misconfiguration: SECRET_KEY is the dev default")
