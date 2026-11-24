"""VIP badge page /invite/<token>/badge/ (entry-badges spec 2026-11-24): print page
with the same validity rules (uniform 404) and QR data as the invite page."""

import pytest

from core.content import CONTENT
from invitations.models import Invitation

pytestmark = pytest.mark.django_db


def make_invitation(status=Invitation.Status.SENT, **kwargs):
    defaults = dict(guest_name="ضيف", organization="جهة", contact_email="vip@example.com")
    defaults.update(kwargs)
    return Invitation.objects.create(status=status, **defaults)


def test_vip_badge_renders(client):
    invitation = make_invitation()
    response = client.get(f"/invite/{invitation.token}/badge/")
    assert response.status_code == 200
    body = response.content.decode()
    assert invitation.guest_name in body
    assert invitation.organization in body
    assert "<svg" in body
    assert CONTENT["BADGE_GUEST"] in body
    assert "no-store" in response.headers["Cache-Control"]


def test_vip_badge_404_for_unknown_and_revoked(client):
    revoked = make_invitation(status=Invitation.Status.REVOKED)
    r_unknown = client.get("/invite/totally-unknown-token-000/badge/")
    r_revoked = client.get(f"/invite/{revoked.token}/badge/")
    assert r_unknown.status_code == r_revoked.status_code == 404


def test_invite_page_links_to_badge(client):
    invitation = make_invitation()
    assert (
        f"/invite/{invitation.token}/badge/"
        in client.get(f"/invite/{invitation.token}/").content.decode()
    )
