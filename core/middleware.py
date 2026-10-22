"""Origin shield: in production every request must come through Cloudflare.

Security review 2026-10-22 (finding M1): the Cloud Run URL is publicly reachable, so
without this check an attacker could talk to the origin directly — bypassing
Cloudflare's rate limits and Turnstile edge rules, and spoofing the CF-Connecting-IP
header that the vote's per-IP burst detection hashes.

A Cloudflare Transform Rule adds a secret ``X-Origin-Token`` header to every proxied
request (docs/operations.md → Cloudflare checklist). When ``CF_ORIGIN_TOKEN`` is set,
requests without that exact header are rejected. Empty setting = disabled (local
development, and production until Cloudflare is configured).

Exempt paths, which are called directly at the origin on purpose:
  /healthz    — uptime checks and the deploy smoke test
  /internal/  — Cloud Scheduler ticks; authenticated by their own INTERNAL_TOKEN
"""

import hmac

from django.conf import settings
from django.http import HttpResponseForbidden

EXEMPT_PREFIXES = ("/healthz", "/internal/")


class CloudflareOriginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = settings.CF_ORIGIN_TOKEN
        if token and not request.path.startswith(EXEMPT_PREFIXES):
            sent = request.headers.get("X-Origin-Token", "")
            if not hmac.compare_digest(sent, token):
                return HttpResponseForbidden()
        return self.get_response(request)
