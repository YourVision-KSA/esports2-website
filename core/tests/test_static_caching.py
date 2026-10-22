"""WhiteNoise long-cache rule (esports/settings/base.py → _immutable_static)."""

from django.conf import settings

immutable = settings.WHITENOISE_IMMUTABLE_FILE_TEST


def test_vite_and_django_hashed_files_are_immutable():
    assert immutable("", "/static/dist/assets/scene-COD0090b.js")
    assert immutable("", "/static/dist/assets/qr-worker-DvoSHGXG.js")
    assert immutable("", "/static/css/base.3f26d9d203f9.css")


def test_unhashed_files_are_not():
    assert not immutable("", "/static/css/base.css")
    assert not immutable("", "/static/dist/.vite/manifest.json")
