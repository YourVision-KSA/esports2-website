"""URL map — mirrors docs/routes.md exactly. Admin lives at /staff/ (not /admin/)."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from core import views as core_views

# In production the Django admin requires a verified TOTP device
# (CLAUDE.md hard rule 4). Locally this can be relaxed via REQUIRE_2FA=False.
if settings.REQUIRE_2FA:
    from django_otp.admin import OTPAdminSite

    admin.site.__class__ = OTPAdminSite

urlpatterns = [
    path("", core_views.home, name="home"),
    path("healthz", core_views.healthz, name="healthz"),
    path("credits/", core_views.credits, name="credits"),
    path("privacy/", core_views.privacy, name="privacy"),
    path("vote/", include("voting.urls")),
    path("register/", include("registration.urls")),
    path("r/", include("registration.manage_urls")),
    path("bracket/", include("bracket.urls")),
    path("api/", include("bracket.api_urls")),
    path("invite/", include("invitations.urls")),
    path("staff/results/", include("bracket.staff_urls")),
    path("staff/checkin/", include("invitations.staff_urls")),
    path("staff/", admin.site.urls),
    path("internal/", include("core.internal_urls")),
]

handler404 = "core.views.error_404"
handler500 = "core.views.error_500"
handler403 = "core.views.error_403"
