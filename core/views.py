"""Core views: home page, health check, error pages, internal scheduler endpoints.

Cache policy follows docs/routes.md: edge-cached pages must carry no per-visitor
state — no CSRF token, no Set-Cookie (CLAUDE.md hard rule 8).
"""

from django.conf import settings
from django.db import connection
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Game
from .outbox import send_due


@cache_control(public=True, max_age=60, s_maxage=60)
def home(request):
    """The single long home page. No forms here (docs/routes.md rule zero)."""
    from .phases import Phase, current_phase

    games = Game.objects.filter(status=Game.Status.CONFIRMED)
    if not games.exists():
        # Before the vote result, show the candidates instead.
        games = Game.objects.filter(status=Game.Status.CANDIDATE)

    # LIVE bar (event days only): the next match that has both players.
    live_match = None
    if current_phase() == Phase.EVENT:
        from bracket.models import Match

        live_match = (
            Match.objects.filter(
                status=Match.Status.PENDING, player1__isnull=False, player2__isnull=False
            )
            .select_related("game", "player1", "player2")
            .order_by("round", "slot")
            .first()
        )
    return render(request, "core/home.html", {"games": games, "live_match": live_match})


def healthz(request):
    """Uptime check: 200 + DB ping (docs/routes.md)."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return HttpResponse("ok")


def phase_closed(request, message_key: str = "PHASE_SOON"):
    """Generic closed-state page used by the phase gate on GETs."""
    return render(request, "core/closed.html", {"message_key": message_key})


@csrf_exempt  # authenticated by the shared INTERNAL_TOKEN, called by Cloud Scheduler
@require_POST
def internal_outbox(request):
    """Scheduler tick: deliver due outbox emails (docs/operations.md)."""
    token = request.headers.get("X-Internal-Token", "")
    if not settings.INTERNAL_TOKEN or token != settings.INTERNAL_TOKEN:
        return HttpResponseForbidden()
    return JsonResponse({"sent": send_due()})


def error_404(request, exception=None):
    return render(request, "core/404.html", status=404)


def error_403(request, exception=None):
    return render(request, "core/403.html", status=403)


def error_500(request):
    return render(request, "core/500.html", status=500)
