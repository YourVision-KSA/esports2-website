"""The {% vite_js %} tag (core/templatetags/vite.py): hashed path from the
manifest when built, silence when not — the page must work without the bundle."""

import core.templatetags.vite as vite_mod
from core.templatetags.vite import vite_js


def test_vite_js_resolves_manifest_entry(monkeypatch):
    monkeypatch.setattr(
        vite_mod, "_manifest", lambda: {"src/main.js": {"file": "assets/main-abc123.js"}}
    )
    tag = vite_js("src/main.js")
    assert 'type="module"' in tag
    assert "/static/dist/assets/main-abc123.js" in tag


def test_vite_js_empty_when_not_built(monkeypatch):
    monkeypatch.setattr(vite_mod, "_manifest", dict)
    assert vite_js("src/main.js") == ""
