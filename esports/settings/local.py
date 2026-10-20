"""Local development settings."""

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = ["*"]

# Print emails to the console instead of sending (outbox still records them).
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Plain static storage locally (no manifest requirement before collectstatic).
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
