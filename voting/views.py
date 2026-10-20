"""Vote views (docs/routes.md). All BYPASS routes: no-store, CSRF as normal.

Voter token: 128-bit random value in a signed, HttpOnly, Secure cookie
(docs/voting.md flow step 1).
"""

import secrets

from django.conf import settings
from django.core import signing
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.views.decorators.cache import never_cache

from core.models import Game
from core.phases import Phase, current_phase
from core.security import client_ip

from . import services, turnstile

COOKIE_SALT = "voter-token"
COOKIE_MAX_AGE = 60 * 60 * 24 * 14  # vote window + margin


def _get_voter_token(request) -> str | None:
    raw = request.COOKIES.get(settings.VOTER_COOKIE_NAME)
    if not raw:
        return None
    try:
        return signing.loads(raw, salt=COOKIE_SALT, max_age=COOKIE_MAX_AGE)
    except signing.BadSignature:
        return None


def _set_voter_cookie(response, token: str):
    response.set_cookie(
        settings.VOTER_COOKIE_NAME,
        signing.dumps(token, salt=COOKIE_SALT),
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
    )


def _asn(request) -> int | None:
    """Cloudflare can forward the origin ASN via a transform rule header."""
    try:
        return int(request.headers.get("X-Client-ASN", ""))
    except (TypeError, ValueError):
        return None


@never_cache
def vote(request):
    phase = current_phase()
    if phase != Phase.VOTE:
        # Writes outside the window are refused regardless of how the request
        # got here (docs/testing.md test_vote_phase_gate).
        if request.method == "POST":
            return HttpResponseForbidden("closed")
        if phase == Phase.PRE:
            return render(request, "core/closed.html", {"message_key": "PHASE_SOON"})
        # After close: show results (docs/voting.md: publish counted + held totals).
        return results(request)

    games = Game.objects.filter(status=Game.Status.CANDIDATE)
    token = _get_voter_token(request)

    if request.method == "POST":
        if not token:
            # Cookie missing/invalid: re-issue and ask to resubmit (one retry).
            token = secrets.token_urlsafe(16)
            response = render(
                request,
                "voting/form.html",
                {
                    "games": games,
                    "error_key": "ERR_RETRY",
                    "turnstile_site_key": settings.TURNSTILE_SITE_KEY,
                    "n_choices": settings.CHOICES_PER_BALLOT,
                },
                status=400,
            )
            _set_voter_cookie(response, token)
            return response

        choice_ids = [int(v) for v in request.POST.getlist("choices") if v.isdigit()]
        ts_ok = turnstile.verify(request.POST.get("cf-turnstile-response", ""), client_ip(request))
        try:
            services.cast_ballot(
                voter_token=token,
                choice_ids=choice_ids,
                turnstile_ok=ts_ok,
                ip=client_ip(request),
                ua=request.headers.get("User-Agent", ""),
                asn=_asn(request),
            )
        except services.AlreadyVoted:
            return render(request, "voting/done.html", {"message_key": "VOTE_DUP"})
        except services.InvalidChoices:
            return render(
                request,
                "voting/form.html",
                {
                    "games": games,
                    "error": True,
                    "turnstile_site_key": settings.TURNSTILE_SITE_KEY,
                    "n_choices": settings.CHOICES_PER_BALLOT,
                },
                status=400,
            )
        # Held ballots see the same success page (docs/voting.md).
        return render(request, "voting/done.html", {"message_key": "VOTE_DONE"})

    # GET: issue the token cookie if the browser has none.
    response = render(
        request,
        "voting/form.html",
        {
            "games": games,
            "turnstile_site_key": settings.TURNSTILE_SITE_KEY,
            "n_choices": settings.CHOICES_PER_BALLOT,
        },
    )
    if not token:
        _set_voter_cookie(response, secrets.token_urlsafe(16))
    return response


@never_cache
def results(request):
    """Totals page — only after the vote closes. The live tally stays hidden."""
    phase = current_phase()
    if phase in (Phase.PRE, Phase.VOTE):
        return render(request, "core/closed.html", {"message_key": "PHASE_SOON"})
    return render(request, "voting/results.html", {"tally": services.tally()})
