"""Invitation views: the public guest page (uniform 404 for unknown/revoked
tokens — no validity oracle) and the door-staff check-in page."""

from django.db.models import Q
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.cache import never_cache

from core import qr
from core.staff import staff_page

from . import services
from .models import Invitation


@never_cache
def invite(request, token):
    invitation = Invitation.objects.filter(
        token=token,
        status__in=[
            Invitation.Status.CREATED,
            Invitation.Status.SENT,
            Invitation.Status.CHECKED_IN,
        ],
    ).first()
    if invitation is None:
        raise Http404  # unknown and revoked look identical (docs/routes.md)
    return render(
        request,
        "invitations/invite.html",
        {"invitation": invitation, "qr_svg": qr.qr_svg(invitation.invite_url())},
    )


@never_cache
def invite_badge(request, token):
    """Print-ready VIP badge (entry-badges spec 2026-11-24). Same validity rules as
    the invite page; the QR data stays the invite URL the door scanner already reads."""
    invitation = Invitation.objects.filter(
        token=token,
        status__in=[
            Invitation.Status.CREATED,
            Invitation.Status.SENT,
            Invitation.Status.CHECKED_IN,
        ],
    ).first()
    if invitation is None:
        raise Http404  # unknown and revoked look identical (docs/routes.md)
    return render(
        request,
        "badges/badge.html",
        {
            "kind": "guest",
            "person_name": invitation.guest_name,
            "subtitle": invitation.organization,
            "qr_svg": qr.qr_svg(invitation.invite_url()),
        },
    )


def _token_from(raw: str) -> str:
    """Accept a bare token or the full invite URL (what a QR code contains)."""
    return raw.strip().rstrip("/").split("/")[-1]


@never_cache
@staff_page("invitations.checkin_invitation")
def staff_checkin(request):
    """Door-staff page (docs/routes.md /staff/checkin/). Two steps, so staff can check
    the guest's ID before anything is recorded:

      1. look up — POST action=lookup (typed/scanned token) or pick from the search list
         → shows the guest card (name, organisation, status); nothing is written
      2. confirm — POST action=confirm → services.check_in (atomic, single-use, audited)

    One page for both QR kinds (entry-badges spec 2026-11-24): VIP invitation tokens
    and player badge tokens (registration.services.check_in). Tokens are 128-bit
    random, so a lookup that matches no invitation falls through to the players.

    (The camera scanner, cut-list item 1, will feed step 1; this page works without it.)"""
    from registration import services as registration_services

    result = guest = player = player_game = None
    if request.method == "POST":
        token = _token_from(request.POST.get("token", ""))
        if request.POST.get("action") == "confirm":
            if request.POST.get("kind") == "player":
                result, player = registration_services.check_in(token, request.user)
                player_game = _confirmed_game(player)
            else:
                result, guest = services.check_in(token, request.user)
        else:
            guest = Invitation.objects.filter(token=token).first() if token else None
            if guest is not None:
                if guest.status in (Invitation.Status.CREATED, Invitation.Status.REVOKED):
                    result, guest = services.CheckInResult.INVALID, None
                elif guest.status == Invitation.Status.CHECKED_IN:
                    result = services.CheckInResult.ALREADY
                else:
                    result = "lookup"  # sent → show the card with the confirm button
            else:
                result, player = _player_lookup(token)
                player_game = _confirmed_game(player)

    query = request.GET.get("q", "").strip()
    guests = Invitation.objects.none()
    if query:
        guests = Invitation.objects.filter(
            Q(guest_name__icontains=query) | Q(organization__icontains=query)
        ).order_by("guest_name")[:20]
    return render(
        request,
        "staff/checkin.html",
        {
            "result": result,
            "guest": guest,
            "player": player,
            "player_game": player_game,
            "query": query,
            "guests": guests,
        },
    )


def _player_lookup(token):
    """Step-1 lookup for a player badge token: shows the card, writes nothing.
    Mirrors registration.services.check_in's gating: only a player holding a
    CONFIRMED seat is valid at the door."""
    from registration.models import Player, Registration

    player = (
        Player.objects.filter(checkin_token=token).select_related("checked_in_by").first()
        if token
        else None
    )
    if (
        player is None
        or not Registration.objects.filter(
            player=player, status=Registration.Status.CONFIRMED
        ).exists()
    ):
        return services.CheckInResult.INVALID, None
    if player.checked_in_at is not None:
        return services.CheckInResult.ALREADY, player
    return "lookup", player


def _confirmed_game(player):
    """Arabic game name for the player card (None when there is no player)."""
    from registration.models import Registration

    if player is None:
        return None
    registration = (
        Registration.objects.filter(player=player, status=Registration.Status.CONFIRMED)
        .select_related("game")
        .first()
    )
    return registration.game.name_ar if registration else None
