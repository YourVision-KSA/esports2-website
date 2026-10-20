"""
Site phases, derived from SiteConfig datetimes (docs/product.md §4).

Boundary semantics: an *_opens_at is INCLUSIVE, a *_closes_at is EXCLUSIVE —
at exactly vote_opens_at the phase is VOTE; at exactly vote_closes_at it is PERMITS.

Phases are enforced in views on every request. The scheduler is a convenience,
never the enforcement mechanism (CLAUDE.md hard rule 2).
"""

import enum
from functools import wraps

from django.http import HttpResponseForbidden
from django.utils import timezone

from .models import SiteConfig


class Phase(enum.Enum):
    PRE = "pre"
    VOTE = "vote"
    PERMITS = "permits"
    REGISTRATION = "registration"
    EVENT = "event"
    ARCHIVE = "archive"


def current_phase(now=None, config: SiteConfig | None = None) -> Phase:
    """Derive the phase from SiteConfig. Unset datetimes keep earlier phases."""
    now = now or timezone.now()
    cfg = config or SiteConfig.get_solo()

    if cfg.archived:
        return Phase.ARCHIVE

    # Before (or without) a vote window -> PRE
    if not cfg.vote_opens_at or now < cfg.vote_opens_at:
        return Phase.PRE
    if cfg.vote_closes_at and now < cfg.vote_closes_at:
        return Phase.VOTE
    if not cfg.vote_closes_at:
        # Vote opened with no close set: stay in VOTE until configured.
        return Phase.VOTE

    # Vote closed. Before (or without) a registration window -> PERMITS.
    if not cfg.registration_opens_at or now < cfg.registration_opens_at:
        return Phase.PERMITS
    if cfg.registration_closes_at and now < cfg.registration_closes_at:
        return Phase.REGISTRATION
    if not cfg.registration_closes_at:
        return Phase.REGISTRATION

    # Registration closed -> EVENT, until archived.
    return Phase.EVENT


def require_phase(*phases: Phase):
    """Guard a view's writes: outside the allowed phases, POST gets 403 and GET
    renders the generic closed page (tests: docs/testing.md phase-gate cases)."""

    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if current_phase() in phases:
                return view(request, *args, **kwargs)
            if request.method == "POST":
                return HttpResponseForbidden("closed")
            from .views import phase_closed

            return phase_closed(request)

        return wrapped

    return decorator
