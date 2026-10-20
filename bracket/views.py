"""Bracket views (docs/routes.md): public pages (cached 30s), the ONLY JSON
endpoint (cached 10s), and the referee results page (staff, BYPASS).

Public display uses gamer tags (game_player_id), never real names.
"""

from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_control, never_cache

from core.models import Game
from core.phases import Phase, current_phase

from . import services
from .models import Match


def _event_visible() -> bool:
    return current_phase() in (Phase.EVENT, Phase.ARCHIVE)


def _tag(registration) -> str | None:
    return registration.game_player_id if registration else None


@cache_control(public=True, max_age=30, s_maxage=30)
def overview(request):
    if not _event_visible():
        return render(request, "core/closed.html", {"message_key": "PHASE_SOON"})
    games = Game.objects.filter(status=Game.Status.CONFIRMED)
    return render(request, "bracket/overview.html", {"games": games})


@cache_control(public=True, max_age=30, s_maxage=30)
def detail(request, slug):
    if not _event_visible():
        return render(request, "core/closed.html", {"message_key": "PHASE_SOON"})
    from core.content import CONTENT

    game = get_object_or_404(Game, slug=slug, status=Game.Status.CONFIRMED)
    by_round: dict[int, list[Match]] = {}
    for match in game.matches.select_related("player1", "player2", "winner"):
        by_round.setdefault(match.round, []).append(match)
    rounds = [
        (num, CONTENT["ROUND_NAMES"].get(num, f"R{num}"), matches)
        for num, matches in sorted(by_round.items())
    ]
    final = by_round.get(4, [None])[0]
    champion = _tag(final.winner) if final and final.winner else None
    return render(
        request, "bracket/detail.html", {"game": game, "rounds": rounds, "champion": champion}
    )


@cache_control(public=True, max_age=10, s_maxage=10)
def api_bracket(request, slug):
    """Flat match list for polling (docs/routes.md). Gamer tags only — no PII."""
    if not _event_visible():
        return JsonResponse({"matches": []})
    game = get_object_or_404(Game, slug=slug, status=Game.Status.CONFIRMED)
    matches = [
        {
            "round": m.round,
            "slot": m.slot,
            "p1": _tag(m.player1),
            "p2": _tag(m.player2),
            "winner": _tag(m.winner),
            "score": m.score_text,
            "status": m.status,
        }
        for m in game.matches.select_related("player1", "player2", "winner")
    ]
    return JsonResponse({"game": game.slug, "matches": matches})


@never_cache
@permission_required("bracket.change_match", raise_exception=True)
def staff_results(request):
    """Mobile-friendly result entry for referees (docs/routes.md /staff/results/)."""
    if request.method == "POST":
        match = get_object_or_404(Match, pk=request.POST.get("match_id"))
        winner_id = request.POST.get("winner_id")
        participants = {str(match.player1_id): match.player1, str(match.player2_id): match.player2}
        winner = participants.get(winner_id)
        if winner is None:
            return render(
                request,
                "staff/results.html",
                {"pending": _pending(), "error": "invalid winner"},
                status=400,
            )
        try:
            services.enter_result(match, winner, request.POST.get("score", ""), actor=request.user)
        except ValidationError as exc:
            return render(
                request,
                "staff/results.html",
                {"pending": _pending(), "error": str(exc)},
                status=400,
            )
        return redirect("staff-results")
    return render(request, "staff/results.html", {"pending": _pending()})


def _pending():
    return (
        Match.objects.filter(
            status=Match.Status.PENDING, player1__isnull=False, player2__isnull=False
        )
        .select_related("game", "player1", "player2")
        .order_by("game__display_order", "round", "slot")
    )
