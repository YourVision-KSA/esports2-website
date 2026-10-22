"""
Base settings shared by all environments.

Environment-specific files (local.py, production.py) import * from here and
override. Secrets come ONLY from environment variables (CLAUDE.md rule).
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
# Read .env from the project root if present (local development convenience).
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-only-change-me")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Staff two-factor auth (CLAUDE.md hard rule 4)
    "django_otp",
    "django_otp.plugins.otp_totp",
    # Project apps (docs/architecture.md boundaries)
    "core",
    "voting",
    "registration",
    "bracket",
    "invitations",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Rejects requests that bypassed Cloudflare (active only when CF_ORIGIN_TOKEN is set)
    "core.middleware.CloudflareOriginMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "esports.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # All Arabic user-facing text + current phase (CLAUDE.md rule 1)
                "core.context.site_context",
            ],
        },
    },
]

WSGI_APPLICATION = "esports.wsgi.application"

# One managed PostgreSQL database; the only source of truth (docs/architecture.md).
DATABASES = {
    "default": env.db(
        "DATABASE_URL", default="postgres://postgres:postgres@127.0.0.1:5432/esports"
    ),
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Times: store UTC, display Riyadh (CLAUDE.md hard rule 6).
LANGUAGE_CODE = "ar"
TIME_ZONE = "Asia/Riyadh"
USE_I18N = False  # strings come from core/content.py, not gettext
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"


def _immutable_static(path: str, url: str) -> bool:
    """Files WhiteNoise may cache for a year (docs/routes.md → Static assets).
    Django's hashed copies (name.<12 hex>.ext) plus Vite's output in /static/dist/assets/,
    whose names are already content-hashed (name-<hash>.js) and are imported by those
    exact names from other chunks, so they must stay unrenamed."""
    import re

    return url.startswith(STATIC_URL + "dist/assets/") or bool(re.search(r"\.[0-9a-f]{12}\.", url))


WHITENOISE_IMMUTABLE_FILE_TEST = _immutable_static
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Hashed filenames so /static/* can be cached for 1 year (docs/routes.md)
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Email: senders go through the OutboxEmail table, never inline (docs/data-model.md).
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@localhost")

LOGIN_URL = "/staff/login/"

# ---------------------------------------------------------------------------
# Project settings (documented in docs/voting.md and docs/data-model.md)
# ---------------------------------------------------------------------------

# HMAC salt for hashing IPs/UAs. Raw values are NEVER stored (CLAUDE.md rule 7).
SIGNALS_SALT = env("SIGNALS_SALT", default="dev-only-salt")

# Voting (docs/voting.md). CHOICES_PER_BALLOT is provisional — DEC-03.
CHOICES_PER_BALLOT = env.int("CHOICES_PER_BALLOT", default=3)
VOTE_IP_HOURLY_LIMIT = env.int("VOTE_IP_HOURLY_LIMIT", default=5)
VOTE_UA_IP_10MIN_LIMIT = env.int("VOTE_UA_IP_10MIN_LIMIT", default=3)
VOTER_COOKIE_NAME = "vt"

# Cloudflare Turnstile. When disabled (local dev), the server treats the
# challenge as passed. In production it MUST be enabled.
TURNSTILE_ENABLED = env.bool("TURNSTILE_ENABLED", default=True)
TURNSTILE_SITE_KEY = env("TURNSTILE_SITE_KEY", default="")
TURNSTILE_SECRET = env("TURNSTILE_SECRET", default="")

# Shared secret for scheduler-called endpoints (/internal/...).
INTERNAL_TOKEN = env("INTERNAL_TOKEN", default="")

# Secret header a Cloudflare Transform Rule adds to every proxied request
# (docs/operations.md → Cloudflare checklist). When set, requests that did not come
# through Cloudflare are rejected (core/middleware.py) and CF-Connecting-IP becomes
# trustworthy (core/security.py). Empty = disabled (local dev; pre-Cloudflare).
CF_ORIGIN_TOKEN = env("CF_ORIGIN_TOKEN", default="")

# Outbox retry policy (docs/data-model.md).
OUTBOX_MAX_ATTEMPTS = 5

# Require TOTP for /staff/ (True in production).
REQUIRE_2FA = env.bool("REQUIRE_2FA", default=False)

# Base URL used when building absolute links in emails (manage links, invites).
SITE_BASE_URL = env("SITE_BASE_URL", default="http://127.0.0.1:8000")
