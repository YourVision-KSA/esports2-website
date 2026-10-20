"""Registration views (docs/routes.md): choose game -> form -> manage page.

All BYPASS routes (no-store). The manage link is the player's only credential;
wrong tokens get a uniform 404 (no oracle).
"""

from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from core.models import Game
from core.phases import Phase, current_phase, require_phase

from . import services
from .models import Player, Registration


@never_cache
def choose(request):
    phase = current_phase()
    if phase != Phase.REGISTRATION:
        key = "REG_CLOSED" if phase in (Phase.EVENT, Phase.ARCHIVE) else "PHASE_SOON"
        return render(request, "core/closed.html", {"message_key": key})
    games = Game.objects.filter(status=Game.Status.CONFIRMED)
    rows = [(g, services.seats_left(g)) for g in games]
    return render(request, "registration/choose.html", {"rows": rows})


@never_cache
@require_phase(Phase.REGISTRATION)
def register_form(request, slug):
    from .forms import RegistrationForm

    game = get_object_or_404(Game, slug=slug, status=Game.Status.CONFIRMED)

    if request.method == "POST":
        form = RegistrationForm(request.POST, game=game)
        if form.is_valid():
            try:
                registration, raw_token = services.register(
                    full_name=form.cleaned_data["full_name"],
                    phone=form.cleaned_data["phone"],
                    email=form.cleaned_data["email"],
                    game=game,
                    game_player_id=form.cleaned_data["game_player_id"],
                )
            except services.DuplicateRegistration:
                return render(
                    request,
                    "registration/form.html",
                    {"form": form, "game": game, "error_key": "REG_DUP_TOURNAMENT"},
                    status=400,
                )
            except services.GameFull:
                return render(
                    request,
                    "registration/form.html",
                    {"form": form, "game": game, "error_key": "REG_FULL"},
                    status=400,
                )
            if raw_token:
                return redirect(f"/r/{raw_token}/?new=1")
            # Existing player (same phone, e.g. re-registering after a withdrawal):
            # their original manage link stays valid — we never re-show tokens.
            return render(
                request, "registration/success_existing.html", {"registration": registration}
            )
    else:
        form = RegistrationForm(game=game)

    return render(
        request,
        "registration/form.html",
        {"form": form, "game": game, "seats_left": services.seats_left(game)},
    )


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
