"""Invitation views: the public guest page (uniform 404 for unknown/revoked
tokens — no validity oracle) and the door-staff check-in page."""

from django.contrib.auth.decorators import permission_required
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render
from django.utils.safestring import mark_safe
from django.views.decorators.cache import never_cache

from . import services
from .models import Invitation


def _qr_svg(url: str) -> str:
    """Inline SVG QR code (docs/routes.md: "QR code ... as inline SVG").

    SVG needs no imaging library — the previous PNG path required Pillow, which is not
    a dependency, so every valid invitation page crashed with a 500."""
    import qrcode
    from qrcode.image.svg import SvgPathImage

    img = qrcode.make(url, image_factory=SvgPathImage, border=0)
    # markup is generated here from our own URL, never from user input → safe to inline
    return mark_safe(img.to_string(encoding="unicode"))


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
        {"invitation": invitation, "qr_svg": _qr_svg(invitation.invite_url())},
    )


def _token_from(raw: str) -> str:
    """Accept a bare token or the full invite URL (what a QR code contains)."""
    return raw.strip().rstrip("/").split("/")[-1]


@never_cache
@permission_required("invitations.change_invitation", raise_exception=True)
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
