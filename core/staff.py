"""Gate for the custom staff pages (/staff/results/, /staff/checkin/).

Audit 2026-11-13, finding 8: these pages checked only a model permission, so their
2FA protection depended on the admin login being the only way in. This gate checks it
itself: the user must be staff, hold the permission, and — when REQUIRE_2FA is on (always
in production) — have verified a TOTP device in this session (django_otp's OTPMiddleware
sets user.is_verified()). Anything else gets 403, like permission_required(raise_exception).
"""

from functools import wraps

from django.conf import settings
from django.core.exceptions import PermissionDenied


def staff_page(perm: str):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            user = request.user
            if not (user.is_authenticated and user.is_active and user.is_staff):
                raise PermissionDenied
            if not user.has_perm(perm):
                raise PermissionDenied
            if settings.REQUIRE_2FA and not getattr(user, "is_verified", lambda: False)():
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapped

    return decorator
