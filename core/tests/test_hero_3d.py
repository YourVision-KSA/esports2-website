"""Hero 3D wiring (docs/frontend.md → 3D scenes): the page must work, unchanged, whether
or not the Vite bundle and the model are present — 3D is progressive enhancement only."""

import json

import pytest

from conftest import set_phase
from core.phases import Phase
from core.templatetags import ui

pytestmark = pytest.mark.django_db


@pytest.fixture
def built_bundle(tmp_path, monkeypatch):
    """Pretend `npm run build` ran and the model is shipped."""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"hero.js": {"file": "assets/hero-abc123.js", "isEntry": True}}))
    model = tmp_path / "controller.glb"
    model.write_bytes(b"glTF")
    files = {ui._VITE_MANIFEST: str(manifest), "models/controller.glb": str(model)}
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
    assert b"data-model=" not in response.content
    assert b"scene-frame" in response.content  # the poster is always there


def test_home_with_bundle_loads_hero_module_and_model(client, built_bundle):
    set_phase(Phase.PRE)
    response = client.get("/")
    body = response.content.decode()
    assert '<script type="module" src="/static/dist/assets/hero-abc123.js"></script>' in body
    assert 'data-model="/static/models/controller.glb"' in body


def test_home_with_bundle_stays_cacheable(client, built_bundle):
    """Adding the 3D must not add per-visitor state to the edge-cached page (rule 8)."""
    set_phase(Phase.PRE)
    response = client.get("/")
    assert "Set-Cookie" not in response.headers
    assert "max-age=60" in response.headers["Cache-Control"]


def test_model_credit_in_footer_only_and_no_template_leaks(client, built_bundle):
    """CC BY 4.0 credit stays on the page (footer), and no raw template syntax leaks
    (Django's {# #} comments are single-line only — multi-line ones render as text)."""
    set_phase(Phase.PRE)
    body = client.get("/").content.decode()
    assert body.count("miwaVV") == 1
    assert "scene-credit" not in body
    assert "{#" not in body and "{%" not in body
