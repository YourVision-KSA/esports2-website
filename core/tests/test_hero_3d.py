"""Hero 3D wiring (docs/frontend.md → 3D scenes): the page must work, unchanged, whether
or not the Vite bundle is present — 3D is progressive enhancement only."""

import json

import pytest

from conftest import set_phase
from core.phases import Phase
from core.templatetags import ui

pytestmark = pytest.mark.django_db


@pytest.fixture
def built_bundle(tmp_path, monkeypatch):
    """Pretend `npm run build` ran."""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"hero.js": {"file": "assets/hero-abc123.js", "isEntry": True}}))
    files = {ui._VITE_MANIFEST: str(manifest)}
    monkeypatch.setattr(ui, "find", lambda path: files.get(path))
    ui._vite_manifest.cache_clear()
    yield
    ui._vite_manifest.cache_clear()


@pytest.fixture
def no_bundle(monkeypatch):
    monkeypatch.setattr(ui, "find", lambda path: None)
    ui._vite_manifest.cache_clear()
    yield
    ui._vite_manifest.cache_clear()


def test_home_without_bundle_has_no_3d_script(client, no_bundle):
    set_phase(Phase.PRE)
    response = client.get("/")
    assert response.status_code == 200
    assert b'type="module"' not in response.content
    assert b"hero-poster.webp" in response.content  # the poster is always there


def test_home_with_bundle_loads_hero_module(client, built_bundle):
    set_phase(Phase.PRE)
    body = client.get("/").content.decode()
    assert '<script type="module" src="/static/dist/assets/hero-abc123.js"></script>' in body
    assert 'id="hero-scene"' in body


def test_home_with_bundle_stays_cacheable(client, built_bundle):
    """Adding the 3D must not add per-visitor state to the edge-cached page (rule 8)."""
    set_phase(Phase.PRE)
    response = client.get("/")
    assert "Set-Cookie" not in response.headers
    assert "max-age=60" in response.headers["Cache-Control"]


def test_no_third_party_model_credit_and_no_template_leaks(client, built_bundle):
    """The controller is built in code (no third-party model → no credit line), and no raw
    template syntax leaks (Django's {# #} comments are single-line only)."""
    set_phase(Phase.PRE)
    body = client.get("/").content.decode()
    assert "CC BY" not in body and "3D model" not in body
    assert "{#" not in body and "{%" not in body
