"""Resolve the Vite-built 3D bundle (docs/frontend.md → Build).

`npm run build` in frontend/ writes hashed files plus `.vite/manifest.json`
into static/dist/ (committed — production has no Node). This tag turns the
stable entry name into a <script type="module"> for the hashed file. If the
bundle was never built the tag renders nothing: the page must work without 3D,
the posters simply stay (FALLBACK tier).
"""

import json

from django import template
from django.conf import settings
from django.contrib.staticfiles.finders import find
from django.templatetags.static import static
from django.utils.html import format_html

register = template.Library()

_cache = None


def _manifest():
    global _cache
    if _cache is None or settings.DEBUG:  # DEBUG: re-read so rebuilds show up
        path = find("dist/.vite/manifest.json")
        if not path:
            return {}
        with open(path, encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


@register.simple_tag
def vite_js(entry):
    """Module script tag for a Vite entry ('' when the bundle isn't built)."""
    info = _manifest().get(entry)
    if not info:
        return ""
    return format_html(
        '<script type="module" src="{}" defer></script>',
        static(f"dist/{info['file']}"),
    )
