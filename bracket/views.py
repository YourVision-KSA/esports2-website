"""Bracket views (docs/routes.md): public pages (cached 30s), the ONLY JSON
endpoint (cached 10s), and the referee results page (staff, BYPASS).

Public display uses gamer tags (game_player_id), never real names.
"""

from urllib.parse import urlencode

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


SCORE_MAX = Match._meta.get_field("score_text").max_length


@never_cache
@permission_required("bracket.change_match", raise_exception=True)
def staff_results(request):
    """Mobile-friendly result entry for referees (docs/routes.md /staff/results/).

    GET lists playable matches (both players known, still pending), optionally filtered
    by ?game=<slug>. POST enters one result through services.enter_result (locked,
    audited) and redirects back (POST/redirect/GET) with a confirmation message."""
    from django.contrib import messages

    from core.content import CONTENT

    game_slug = request.GET.get("game") or request.POST.get("game") or ""
    back = redirect(request.path + (f"?{urlencode({'game': game_slug})}" if game_slug else ""))

    if request.method == "POST":
        match = get_object_or_404(Match, pk=request.POST.get("match_id"))
        participants = {str(match.player1_id): match.player1, str(match.player2_id): match.player2}
        winner = participants.get(request.POST.get("winner_id", ""))
        if winner is None:
            messages.error(request, CONTENT["STAFF_ERR_WINNER"])
            return back
        try:
            services.enter_result(
                match, winner, request.POST.get("score", "").strip()[:SCORE_MAX], actor=request.user
            )
        except ValidationError:
            # e.g. the match was entered meanwhile from another phone (match no longer pending)
            messages.error(request, CONTENT["STAFF_ERR_SAVE"])
            return back
        messages.success(
            request, CONTENT["STAFF_RESULT_SAVED"].replace("{winner}", winner.game_player_id)
        )
        return back

    pending = _pending()
    games = Game.objects.filter(status=Game.Status.CONFIRMED).order_by("display_order")
    counts = {g.slug: 0 for g in games}
    for m in pending:
        counts[m.game.slug] = counts.get(m.game.slug, 0) + 1
    if game_slug:
        pending = [m for m in pending if m.game.slug == game_slug]
    matches = [
        {
            "obj": m,
            "round_name": CONTENT["ROUND_NAMES"].get(m.round, f"R{m.round}"),
            "label": CONTENT["STAFF_MATCH"].replace("{n}", str(m.slot)),
        }
        for m in pending
    ]
    return render(
        request,
        "staff/results.html",
        {
            "matches": matches,
            "games": [(g, counts.get(g.slug, 0)) for g in games],
            "active_game": game_slug,
            "total_pending": sum(counts.values()),
        },
    )


def _pending():
    return list(
        Match.objects.filter(
            status=Match.Status.PENDING, player1__isnull=False, player2__isnull=False
        )
        .select_related("game", "player1", "player2")
        .order_by("game__display_order", "round", "slot")
    )
