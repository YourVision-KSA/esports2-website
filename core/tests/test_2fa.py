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


class TTY(StringIO):
    """An output that says it is an interactive terminal."""

    def isatty(self):
        return True


def test_enroll_creates_confirmed_device_and_prints_url_to_a_terminal(admin_user):
    out = TTY()
    call_command("enroll_totp", admin_user.username, stdout=out)

    device = TOTPDevice.objects.get(user=admin_user)
    assert device.confirmed
    assert "otpauth://totp/" in out.getvalue()
    # The secret the staff member scans actually verifies a live token.
    assert device.verify_token(current_token(device))


def test_enroll_never_prints_the_secret_to_a_non_terminal(admin_user):
    """Audit 2026-11-13: run as a Cloud Run job, stdout goes to Cloud Logging — the
    permanent TOTP secret must not end up there."""
    out = StringIO()
    with pytest.raises(CommandError, match="non-interactive"):
        call_command("enroll_totp", admin_user.username, stdout=out)
    assert "otpauth://" not in out.getvalue()
    assert not TOTPDevice.objects.exists()


def test_enroll_can_write_the_url_to_a_private_file(admin_user, tmp_path):
    target = tmp_path / "totp-url.txt"
    out = StringIO()
    call_command("enroll_totp", admin_user.username, "--url-file", str(target), stdout=out)
    assert "otpauth://" not in out.getvalue()
    assert target.read_text().startswith("otpauth://totp/")
    assert (target.stat().st_mode & 0o777) == 0o600


def test_enroll_refuses_non_staff(django_user_model):
    django_user_model.objects.create_user("visitor", password="x", is_staff=False)
    with pytest.raises(CommandError, match="not staff"):
        call_command("enroll_totp", "visitor")
    assert not TOTPDevice.objects.exists()


def test_enroll_refuses_unknown_user():
    with pytest.raises(CommandError, match="No user"):
        call_command("enroll_totp", "nobody")


def test_enroll_requires_replace_to_rotate(admin_user):
    call_command("enroll_totp", admin_user.username, stdout=TTY())
    old_key = TOTPDevice.objects.get(user=admin_user).key

    with pytest.raises(CommandError, match="--replace"):
        call_command("enroll_totp", admin_user.username, stdout=TTY())
    assert TOTPDevice.objects.get(user=admin_user).key == old_key  # unchanged

    call_command("enroll_totp", admin_user.username, "--replace", stdout=TTY())
    device = TOTPDevice.objects.get(user=admin_user)  # exactly one device remains
    assert device.key != old_key


def test_unwritable_url_file_changes_nothing(admin_user, tmp_path):
    """Pre-merge review: with --replace the old device used to be deleted and a new one
    created BEFORE the file was opened — a bad path locked the user out (the new secret
    was shown to nobody). The path is now checked first."""
    call_command("enroll_totp", admin_user.username, stdout=TTY())
    old_key = TOTPDevice.objects.get(user=admin_user).key

    target = tmp_path / "no-such-folder" / "totp-url.txt"
    with pytest.raises(CommandError, match="nothing was changed"):
        call_command("enroll_totp", admin_user.username, "--replace", "--url-file", str(target))
    assert TOTPDevice.objects.get(user=admin_user).key == old_key  # still the old device
    assert not target.exists()


def test_unwritable_url_file_creates_no_first_device(admin_user, tmp_path):
    target = tmp_path / "no-such-folder" / "totp-url.txt"
    with pytest.raises(CommandError, match="nothing was changed"):
        call_command("enroll_totp", admin_user.username, "--url-file", str(target))
    assert not TOTPDevice.objects.exists()
