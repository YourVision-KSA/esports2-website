"""The /staff/login/ form: one generic answer, and a failure throttle
(security assessment 2026-11-19, YV-38).

Two problems with the stock django-otp admin login:

1. It checked the password first and, when it was right, asked for the OTP code. That
   second page confirmed a correct (possibly reused) password to anyone, before the
   second factor.
2. Nothing in the application limited guesses; only a Cloudflare rule was planned.

This form checks the password AND (when REQUIRE_2FA is on — always in production) the
TOTP code in ONE step, and answers every failure — unknown user, wrong password, not
staff, missing or wrong code, device throttled — with the same message and the same
page. Staff type username, password and the 6-digit code together.

Throttle: each failure is stored as a StaffLoginFailure (HMAC hashes only). While the
typed username has STAFF_LOGIN_FAILURES_PER_ACCOUNT failures, or the client network
(IPv4 address / IPv6 /64, core.security.network_key) has
STAFF_LOGIN_FAILURES_PER_NETWORK failures, in the last STAFF_LOGIN_WINDOW_MINUTES, the
password is NOT checked at all and the THROTTLED message is shown. Throttled attempts are
not recorded, so access returns by itself when the window passes. The counts are soft
(two parallel guesses can both pass a check); the Cloudflare rule stays the first line.
Runbook: docs/operations.md → "Staff login throttle".

The admin is in English (Django's admin, USE_I18N = False), so these messages are too.
Both strings are listed in docs/content-ar.md (STAFF-LOGIN-INVALID / STAFF-LOGIN-THROTTLED,
DRAFT) so the owner reviews them like every other user-facing string (CLAUDE.md rule 1).

Residual timing channel (accepted): the OTP check runs only after a correct password, so
"right password + wrong code" answers measurably slower than "wrong password" even though
the pages are byte-identical. The account throttle caps the attempts an attacker can time
(STAFF_LOGIN_FAILURES_PER_ACCOUNT per window), which keeps the sample too small to exploit
in practice; noted so nobody mistakes the identical pages for a complete fix.
"""

from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import StaffLoginFailure
from .security import client_ip, hmac_hash, network_hash

INVALID_LOGIN = (
    "Please enter the correct username, password and authentication code for a staff "
    "account. All fields may be case-sensitive."
)
THROTTLED = "Too many failed sign-in attempts. Please wait a few minutes and try again."


def _window_start():
    return timezone.now() - timedelta(minutes=settings.STAFF_LOGIN_WINDOW_MINUTES)


def _keys(request, username: str) -> tuple[str, str]:
    """(username_hash, network_hash) — never the raw values (CLAUDE.md rule 7)."""
    ip = client_ip(request) if request is not None else ""
    return hmac_hash("staff-login:" + username.strip().lower()), network_hash(ip)


def is_throttled(username_hash: str, net_hash: str) -> bool:
    recent = StaffLoginFailure.objects.filter(created_at__gte=_window_start())
    if (
        recent.filter(username_hash=username_hash).count()
        >= settings.STAFF_LOGIN_FAILURES_PER_ACCOUNT
    ):
        return True
    return recent.filter(network_hash=net_hash).count() >= settings.STAFF_LOGIN_FAILURES_PER_NETWORK


def record_failure(username_hash: str, net_hash: str) -> None:
    StaffLoginFailure.objects.create(username_hash=username_hash, network_hash=net_hash)
    # Housekeeping: rows older than a day can never matter again.
    StaffLoginFailure.objects.filter(created_at__lt=timezone.now() - timedelta(days=1)).delete()


class _CodeInput(forms.TextInput):
    """Never echoes a submitted code back into the page (it is single-use anyway, and an
    echoed code would make the failure pages differ by what was typed)."""

    def format_value(self, value):
        return None


class StaffLoginForm(AdminAuthenticationForm):
    """Admin login form; installed on admin.site in esports/urls.py.

    Field names match django-otp's admin login template (otp/admin111/login.html), which
    OTPAdminSite renders in production. otp_device is optional: with none chosen, the
    code is checked against the user's confirmed devices (staff have exactly one TOTP
    device — core/management/commands/enroll_totp.py)."""

    otp_device = forms.CharField(required=False, widget=forms.Select)
    otp_token = forms.CharField(
        required=False, widget=_CodeInput(attrs={"autocomplete": "one-time-code"})
    )
    otp_challenge = forms.CharField(required=False)  # the template's button; unused

    error_messages = {
        **AdminAuthenticationForm.error_messages,
        "invalid_login": INVALID_LOGIN,
        "throttled": THROTTLED,
    }

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if not username or not password:
            return self.cleaned_data  # "This field is required." on the empty field

        user_key, net_key = _keys(self.request, username)
        if is_throttled(user_key, net_key):
            raise ValidationError(self.error_messages["throttled"], code="throttled")

        user = authenticate(self.request, username=username, password=password)
        ok = user is not None and user.is_active and user.is_staff
        device = None
        if ok and settings.REQUIRE_2FA:
            device = self._verify_otp(user)
            ok = device is not None

        if not ok:
            record_failure(user_key, net_key)
            # get_user() stays None, so the page is identical whatever was wrong (the
            # django-otp template shows the device list only for a known user).
            self.user_cache = None
            raise ValidationError(self.error_messages["invalid_login"], code="invalid_login")

        if device is not None:
            user.otp_device = device  # django_otp marks the session verified on login
        self.user_cache = user
        return self.cleaned_data

    def _verify_otp(self, user):
        """The verified device, or None. Rows are locked (for_verify) so parallel
        guesses cannot slip past django-otp's own failure back-off."""
        from django_otp import devices_for_user
        from django_otp.models import Device

        token = (self.cleaned_data.get("otp_token") or "").strip()
        if not token:
            return None
        with transaction.atomic():
            devices = list(devices_for_user(user, confirmed=True, for_verify=True))
            chosen = self.cleaned_data.get("otp_device")
            if chosen:
                picked = Device.from_persistent_id(chosen, for_verify=True)
                # SECURITY: only ever one of THIS user's confirmed devices.
                devices = [
                    d
                    for d in devices
                    if picked is not None and d.persistent_id == picked.persistent_id
                ]
            for device in devices:
                allowed, _ = device.verify_is_allowed()
                if allowed and device.verify_token(token):
                    return device
        return None
