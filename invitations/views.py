"""Invitation views: the public guest page (uniform 404 for unknown/revoked
tokens — no validity oracle) and the door-staff check-in page."""

import base64
import io

from django.contrib.auth.decorators import permission_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.cache import never_cache

from . import services
from .models import Invitation


def _qr_data_uri(url: str) -> str:
    import qrcode

    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


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
        {"invitation": invitation, "qr": _qr_data_uri(invitation.invite_url())},
    )


@never_cache
@permission_required("invitations.change_invitation", raise_exception=True)
def staff_checkin(request):
    """Door-staff page: manual token entry + guest search. (Camera scanner is
    cut-list item 1; this page is its fallback and ships first.)"""
    result = guest = None
    if request.method == "POST":
        token = request.POST.get("token", "").strip().rstrip("/").split("/")[-1]
        result, guest = services.check_in(token, request.user)

    query = request.GET.get("q", "").strip()
    guests = Invitation.objects.none()
    if query:
        guests = Invitation.objects.filter(
            Q(guest_name__icontains=query) | Q(organization__icontains=query)
        )[:20]
    return render(
        request,
        "staff/checkin.html",
        {"result": result, "guest": guest, "query": query, "guests": guests},
    )
