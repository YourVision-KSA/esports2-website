"""Enroll a staff user in TOTP 2FA from the command line (docs/operations.md step 8).

In production the admin uses OTPAdminSite (esports/urls.py), which refuses login to any
user without a *confirmed* TOTP device — so the first device cannot be added through the
admin itself. This command breaks that chicken-and-egg: run it in a one-off job, scan or
type the printed otpauth:// URL into an authenticator app, then log in normally.

Usage: python manage.py enroll_totp <username>
Re-running for a user who already has a confirmed device refuses, unless --replace is
given (rotating a device after suspected compromise — see docs/operations.md runbook).
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django_otp.plugins.otp_totp.models import TOTPDevice


class Command(BaseCommand):
    help = "Create a TOTP device for a staff user and print the otpauth:// setup URL."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete the user's existing TOTP devices first (device rotation).",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist:
            raise CommandError(f"No user named {options['username']!r}.") from None
        if not user.is_staff:
            raise CommandError(f"{user.username!r} is not staff; refusing to enroll.")

        existing = TOTPDevice.objects.filter(user=user)
        if existing.exists():
            if not options["replace"]:
                raise CommandError(
                    f"{user.username!r} already has a TOTP device. Use --replace to rotate it."
                )
            existing.delete()
            self.stdout.write("Existing device(s) deleted.")

        # confirmed=True: the printed URL is handed to the user directly, there is no
        # separate confirmation step (the admin's own confirm flow is unreachable here).
        device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)
        self.stdout.write(f"TOTP device created for {user.username!r}.")
        self.stdout.write("Add it to an authenticator app via this URL (or type the key):")
        self.stdout.write(device.config_url)
        self.stdout.write(self.style.SUCCESS("Done. The user can now log in at /staff/."))
