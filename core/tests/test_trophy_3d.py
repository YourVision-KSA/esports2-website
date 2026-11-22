"""Trophy 3D wiring (docs/frontend.md → 3D scenes): like the hero scene, the prizes
section must work, unchanged, whether or not the Vite bundle and the trophy model are
present — 3D is progressive enhancement only."""

import json

import pytest

from conftest import set_phase
from core.phases import Phase
from core.templatetags import ui

pytestmark = pytest.mark.django_db


@pytest.fixture
def trophy_shipped(tmp_path, monkeypatch):
    """Pretend `npm run build` ran and only the trophy model is shipped."""
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"hero.js": {"file": "assets/hero-abc123.js", "isEntry": True}}))
    model = tmp_path / "trophy.glb"
    model.write_bytes(b"glTF")
    files = {ui._VITE_MANIFEST: str(manifest), "models/trophy.glb": str(model)}
    monkeypatch.setattr(ui, "find", lambda path: files.get(path))
    ui._vite_manifest.cache_clear()
    yield
    ui._vite_manifest.cache_clear()


@pytest.fixture
def nothing_shipped(monkeypatch):
    monkeypatch.setattr(ui, "find", lambda path: None)
    ui._vite_manifest.cache_clear()
    yield
    ui._vite_manifest.cache_clear()


def test_home_without_model_keeps_trophy_poster_only(client, nothing_shipped):
    set_phase(Phase.PRE)
    body = client.get("/").content.decode()
    assert 'id="trophy-scene"' in body
    assert "data-model=" not in body  # neither scene gets a model
    assert "trophy-frame" in body  # the photo poster panel is always there


def test_home_with_trophy_model_wires_it_independently_of_hero(client, trophy_shipped):
    """The trophy model can ship without the hero model: only #trophy-scene gets data-model."""
    set_phase(Phase.PRE)
    body = client.get("/").content.decode()
    assert 'id="trophy-scene" data-model="/static/models/trophy.glb"' in body
    assert 'id="hero-scene" data-model=' not in body


def test_credits_page_lists_trophy_and_photo_sources(client):
    """The trophy is an original code-built model (no licence to honour); the photo
    sources are listed on /credits/ for completeness."""
    body = client.get("/credits/").content.decode()
    assert "build-trophy.mjs" in body
    assert "Pexels" in body
