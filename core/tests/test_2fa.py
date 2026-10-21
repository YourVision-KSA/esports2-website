"""Staff TOTP enrollment via `enroll_totp` (docs/operations.md step 8, CLAUDE.md rule 4).

In production OTPAdminSite refuses login without a confirmed device, so the first
device must come from this command; these tests prove the printed secret is usable.
"""

from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django_otp.oath import totp
from django_otp.plugins.otp_totp.models import TOTPDevice

pytestmark = pytest.mark.django_db


def current_token(device):
    return str(totp(device.bin_key, step=device.step, t0=device.t0, digits=device.digits))


def test_enroll_creates_confirmed_device_and_prints_url(admin_user):
    out = StringIO()
    call_command("enroll_totp", admin_user.username, stdout=out)

    device = TOTPDevice.objects.get(user=admin_user)
    assert device.confirmed
    assert "otpauth://totp/" in out.getvalue()
    # The secret the staff member scans actually verifies a live token.
    assert device.verify_token(current_token(device))


def test_enroll_refuses_non_staff(django_user_model):
    django_user_model.objects.create_user("visitor", password="x", is_staff=False)
    with pytest.raises(CommandError, match="not staff"):
        call_command("enroll_totp", "visitor")
    assert not TOTPDevice.objects.exists()


def test_enroll_refuses_unknown_user():
    with pytest.raises(CommandError, match="No user"):
        call_command("enroll_totp", "nobody")


def test_enroll_requires_replace_to_rotate(admin_user):
    call_command("enroll_totp", admin_user.username, stdout=StringIO())
    old_key = TOTPDevice.objects.get(user=admin_user).key

    with pytest.raises(CommandError, match="--replace"):
        call_command("enroll_totp", admin_user.username)
    assert TOTPDevice.objects.get(user=admin_user).key == old_key  # unchanged

    call_command("enroll_totp", admin_user.username, "--replace", stdout=StringIO())
    device = TOTPDevice.objects.get(user=admin_user)  # exactly one device remains
    assert device.key != old_key
