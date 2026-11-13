"""Registration views (docs/routes.md): choose game -> form -> manage page.

All BYPASS routes (no-store). The manage link is the player's only credential;
wrong tokens get a uniform 404 (no oracle).
"""

import logging

from django.conf import settings
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from core import privacy, turnstile
from core.models import Game
from core.phases import Phase, current_phase, require_phase
from core.security import client_ip

from . import abuse, services
from .models import Player, Registration, RegistrationAttempt

log = logging.getLogger(__name__)
Outcome = RegistrationAttempt.Outcome


def _registration_open() -> bool:
    """REGISTRATION phase AND a complete privacy notice (core/privacy.py): personal
    data is never collected under an unfinished notice (audit 2026-11-13, finding 4)."""
    if current_phase() != Phase.REGISTRATION:
        return False
    if not privacy.notice_complete():
        log.warning("registration blocked: %s", privacy.STAFF_MESSAGE)
        return False
    return True


@never_cache
def choose(request):
    if not _registration_open():
        # REGISTRATION phase with an unfinished privacy notice also shows REG_CLOSED.
        not_yet = current_phase() in (Phase.PRE, Phase.VOTE, Phase.PERMITS)
        key = "PHASE_SOON" if not_yet else "REG_CLOSED"
        return render(request, "core/closed.html", {"message_key": key})
    games = Game.objects.filter(status=Game.Status.CONFIRMED)
    rows = [(g, services.seats_left(g)) for g in games]
    return render(request, "registration/choose.html", {"rows": rows})


def _form_page(request, form, game, error_key=None, status=200):
    return render(
        request,
        "registration/form.html",
        {
            "form": form,
            "game": game,
            "error_key": error_key,
            "seats_left": services.seats_left(game),
            # The widget is shown only when the server will actually check it.
            "turnstile_site_key": settings.TURNSTILE_SITE_KEY if settings.TURNSTILE_ENABLED else "",
        },
        status=status,
    )


@never_cache
@require_phase(Phase.REGISTRATION)
def register_form(request, slug):
    """GET: the form. POST, cheapest check first (audit 2026-11-13, finding 1):

    1. privacy notice complete (else closed, like any other phase gate)
    2. per-client attempt limit                       → 429, nothing else evaluated
    3. form valid
    4. per-phone attempt limit (counts only attempts that passed Turnstile — otherwise
       a script could lock out someone else's number), per-client registration caps → 429
    5. Turnstile, verified server-side (fail OR outage → reject, player retries;
       docs/architecture.md: registration never goes to a "held" bucket)
    6. the seat transaction (services.register)

    Every POST leaves one RegistrationAttempt row (hashes only) with its outcome.
    """
    from .forms import RegistrationForm

    if not _registration_open():
        if request.method == "POST":
            return HttpResponseForbidden("closed")
        return render(request, "core/closed.html", {"message_key": "REG_CLOSED"})

    game = get_object_or_404(Game, slug=slug, status=Game.Status.CONFIRMED)

    if request.method != "POST":
        return _form_page(request, RegistrationForm(game=game), game)

    ip_h, ua_h = abuse.client_hashes(request)
    attempt = RegistrationAttempt(ip_hash=ip_h, ua_hash=ua_h, game=game)

    def finish(outcome, error_key, status, form):
        attempt.outcome = outcome
        attempt.save()
        return _form_page(request, form, game, error_key=error_key, status=status)

    form = RegistrationForm(request.POST, game=game)
    if abuse.ip_attempts_exceeded(ip_h):
        return finish(Outcome.LIMITED, "REG_RATE_LIMITED", 429, form)
    if not form.is_valid():
        return finish(Outcome.INVALID, None, 200, form)

    attempt.phone_hash = abuse.phone_hash(form.cleaned_data["phone"])
    if abuse.phone_attempts_exceeded(attempt.phone_hash) or abuse.registrations_exceeded(
        ip_h, ua_h
    ):
        return finish(Outcome.LIMITED, "REG_RATE_LIMITED", 429, form)

    passed = turnstile.verify(request.POST.get("cf-turnstile-response", ""), client_ip(request))
    if passed is not True:  # False = failed, None = Turnstile unreachable: both rejected
        return finish(Outcome.TURNSTILE, "ERR_RETRY", 400, form)

    try:
        registration, raw_token = services.register(
            full_name=form.cleaned_data["full_name"],
            phone=form.cleaned_data["phone"],
            email=form.cleaned_data["email"],
            game=game,
            game_player_id=form.cleaned_data["game_player_id"],
        )
    except services.DuplicateRegistration:
        return finish(Outcome.DUPLICATE, "REG_DUP_TOURNAMENT", 400, form)
    except services.GameFull:
        return finish(Outcome.FULL, "REG_FULL", 400, form)

    attempt.outcome = Outcome.REGISTERED
    attempt.registration = registration
    attempt.save()
    if raw_token:
        return redirect(f"/r/{raw_token}/?new=1")
    # Existing player (same phone, e.g. re-registering after a withdrawal):
    # their original manage link stays valid — we never re-show tokens.
    return render(request, "registration/success_existing.html", {"registration": registration})


def _get_registration_or_404(token: str) -> tuple[Player, Registration]:
    player = Player.objects.filter(manage_token_hash=Player.hash_token(token)).first()
    if player is None:
        raise Http404
    registration = (
        player.registrations.filter(status__in=Registration.ACTIVE).first()
        or player.registrations.order_by("-created_at").first()
    )
    if registration is None:
        raise Http404
    return player, registration


@never_cache
def manage(request, token):
    """Player status page. Available registration..event (docs/routes.md)."""
    phase = current_phase()
    if phase in (Phase.PRE, Phase.VOTE, Phase.PERMITS):
        raise Http404
    player, registration = _get_registration_or_404(token)
    return render(
        request,
        "registration/manage.html",
        {
            "player": player,
            "registration": registration,
            "is_new": request.GET.get("new") == "1",
            "manage_token": token,
            "can_withdraw": (
                phase == Phase.REGISTRATION and registration.status in Registration.ACTIVE
            ),
        },
    )


@never_cache
@require_phase(Phase.REGISTRATION)
def withdraw(request, token):
    player, registration = _get_registration_or_404(token)
    if request.method == "POST":
        services.withdraw(registration)
        return render(request, "registration/withdrawn.html")
    return render(
        request,
        "registration/withdraw_confirm.html",
        {"registration": registration, "manage_token": token},
    )
