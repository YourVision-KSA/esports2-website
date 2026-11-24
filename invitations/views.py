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

    (The camera scanner, cut-list item 1, will feed step 1; this page works without it.)"""
    result = guest = None
    if request.method == "POST":
        token = _token_from(request.POST.get("token", ""))
        if request.POST.get("action") == "confirm":
            result, guest = services.check_in(token, request.user)
        else:
            guest = Invitation.objects.filter(token=token).first() if token else None
            if guest is None or guest.status in (
                Invitation.Status.CREATED,
                Invitation.Status.REVOKED,
            ):
                result, guest = services.CheckInResult.INVALID, None
            elif guest.status == Invitation.Status.CHECKED_IN:
                result = services.CheckInResult.ALREADY
            else:
                result = "lookup"  # sent → show the card with the confirm button

    query = request.GET.get("q", "").strip()
    guests = Invitation.objects.none()
    if query:
        guests = Invitation.objects.filter(
            Q(guest_name__icontains=query) | Q(organization__icontains=query)
        ).order_by("guest_name")[:20]
    return render(
        request,
        "staff/checkin.html",
        {"result": result, "guest": guest, "query": query, "guests": guests},
    )
