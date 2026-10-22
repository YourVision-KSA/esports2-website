"""Small presentation helpers for the Arena Night templates."""

import json
from functools import lru_cache

from django import template
from django.conf import settings
from django.contrib.staticfiles.finders import find
from django.templatetags.static import static

register = template.Library()

# Per-game accent for the card rule (docs/frontend.md rev 4: cyan / magenta / gold cycle).
_ACCENTS = ["var(--accent)", "var(--accent-2)", "var(--gold)"]


@register.filter
def game_image(game):
    """Static path of the game-evoking card image; falls back to the default.
    Images are placeholders the owner can swap (docs/frontend.md imagery rule)."""
    path = f"img/games/{game.slug}.jpg"
    return path if find(path) else "img/games/default.jpg"


@register.filter
def accent(counter0):
    return _ACCENTS[counter0 % len(_ACCENTS)]


# --- Vite bundle (docs/frontend.md → Build) -----------------------------------------
# `npm run build` in frontend/ writes static/dist/.vite/manifest.json. The tag maps an
# entry name to its hashed file. No manifest (bundle not built) → empty string, and the
# template simply leaves the 3D out — the page works without it (poster stays).
_VITE_MANIFEST = "dist/.vite/manifest.json"


@lru_cache(maxsize=1)
def _vite_manifest() -> dict:
    path = find(_VITE_MANIFEST)
    if not path:
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


@register.simple_tag
def vite_asset(entry: str) -> str:
    """Static URL of a Vite entry, e.g. {% vite_asset "hero.js" %}; "" if not built."""
    if settings.DEBUG:
        _vite_manifest.cache_clear()  # pick up rebuilds while developing
    chunk = _vite_manifest().get(entry)
    return static(f"dist/{chunk['file']}") if chunk else ""


@register.simple_tag
def static_if_exists(path: str) -> str:
    """Static URL only when the file is actually shipped (e.g. the optional 3D model)."""
    return static(path) if find(path) else ""
