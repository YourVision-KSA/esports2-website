"""Hashing helpers. Raw IPs/UAs are NEVER stored (CLAUDE.md hard rule 7)."""

import hashlib
import hmac

from django.conf import settings


def hmac_hash(value: str) -> str:
    """HMAC-SHA256 of a signal value (IP, UA) with SIGNALS_SALT (docs/voting.md).
    Deleting the salt at end of life makes these permanently unlinkable."""
    return hmac.new(
        settings.SIGNALS_SALT.encode(), (value or "").encode(), hashlib.sha256
    ).hexdigest()


def token_hash(value: str) -> str:
    """SHA-256 for high-entropy tokens (voter tokens, manage tokens). The tokens
    themselves are >=128-bit random, so no salt is needed."""
    return hashlib.sha256((value or "").encode()).hexdigest()


def client_ip(request) -> str:
    """Original client IP. CF-Connecting-IP is authoritative ONLY while requests are
    forced through Cloudflare (CF_ORIGIN_TOKEN set → core/middleware.py rejects direct
    origin hits); otherwise the header is attacker-controlled, so use the socket address."""
    if settings.CF_ORIGIN_TOKEN:
        return request.META.get("HTTP_CF_CONNECTING_IP") or request.META.get("REMOTE_ADDR", "")
    return request.META.get("REMOTE_ADDR", "")
