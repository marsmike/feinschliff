"""Tests for lib.diagrams.renderer — Protocol + RoughRenderer / PlaywrightRenderer."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from feinschliff.diagrams.renderer import (
    PlaywrightRenderer,
    Renderer,
    RoughRenderer,
    choose_renderer,
    register_renderer,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _write_excalidraw(path: Path, elements: list[dict]) -> Path:
    path.write_text(
        json.dumps({"elements": elements, "appState": {}}),
        encoding="utf-8",
    )
    return path


def _simple_excalidraw(path: Path) -> Path:
    return _write_excalidraw(
        path,
        [{"type": "rectangle", "x": 0, "y": 0, "width": 100, "height": 50,
          "id": "r1", "isDeleted": False}],
    )


def _freedraw_excalidraw(path: Path) -> Path:
    return _write_excalidraw(
        path,
        [{"type": "freedraw", "x": 0, "y": 0, "id": "f1", "isDeleted": False}],
    )


def _image_excalidraw(path: Path) -> Path:
    return _write_excalidraw(
        path,
        [{"type": "image", "x": 0, "y": 0, "id": "i1", "isDeleted": False}],
    )


def _frame_excalidraw(path: Path) -> Path:
    return _write_excalidraw(
        path,
        [{"type": "frame", "x": 0, "y": 0, "id": "fr1", "isDeleted": False}],
    )


# ── Protocol conformance ──────────────────────────────────────────────────────

def test_rough_renderer_satisfies_protocol():
    assert isinstance(RoughRenderer(), Renderer)


def test_playwright_renderer_satisfies_protocol():
    assert isinstance(PlaywrightRenderer(), Renderer)


# ── RoughRenderer.supports ────────────────────────────────────────────────────

@patch("feinschliff.diagrams.renderer.RoughRenderer._available", return_value=True)
def test_rough_supports_simple_doc(mock_avail, tmp_path):
    src = _simple_excalidraw(tmp_path / "simple.excalidraw")
    assert RoughRenderer().supports(src) is True


@patch("feinschliff.diagrams.renderer.RoughRenderer._available", return_value=True)
def test_rough_rejects_freedraw(mock_avail, tmp_path):
    src = _freedraw_excalidraw(tmp_path / "freedraw.excalidraw")
    assert RoughRenderer().supports(src) is False


@patch("feinschliff.diagrams.renderer.RoughRenderer._available", return_value=True)
def test_rough_rejects_image(mock_avail, tmp_path):
    src = _image_excalidraw(tmp_path / "image.excalidraw")
    assert RoughRenderer().supports(src) is False


@patch("feinschliff.diagrams.renderer.RoughRenderer._available", return_value=True)
def test_rough_rejects_frame(mock_avail, tmp_path):
    src = _frame_excalidraw(tmp_path / "frame.excalidraw")
    assert RoughRenderer().supports(src) is False


@patch("feinschliff.diagrams.renderer.RoughRenderer._available", return_value=False)
def test_rough_unavailable_when_deps_missing(mock_avail, tmp_path):
    src = _simple_excalidraw(tmp_path / "simple.excalidraw")
    assert RoughRenderer().supports(src) is False


@patch("feinschliff.diagrams.renderer.RoughRenderer._available", return_value=True)
def test_rough_rejects_svg_extension(mock_avail, tmp_path):
    src = tmp_path / "diagram.svg"
    src.write_text("<svg/>", encoding="utf-8")
    assert RoughRenderer().supports(src) is False


# ── PlaywrightRenderer.supports ───────────────────────────────────────────────

def test_playwright_supports_excalidraw(tmp_path):
    src = tmp_path / "x.excalidraw"
    src.write_text("{}", encoding="utf-8")
    assert PlaywrightRenderer().supports(src) is True


def test_playwright_supports_svg(tmp_path):
    src = tmp_path / "x.svg"
    src.write_text("<svg/>", encoding="utf-8")
    assert PlaywrightRenderer().supports(src) is True


def test_playwright_does_not_support_txt(tmp_path):
    src = tmp_path / "x.txt"
    src.write_text("hello", encoding="utf-8")
    assert PlaywrightRenderer().supports(src) is False


# ── choose_renderer ───────────────────────────────────────────────────────────

@patch("feinschliff.diagrams.renderer.RoughRenderer._available", return_value=True)
def test_choose_renderer_picks_rough_for_simple_doc(mock_avail, tmp_path):
    src = _simple_excalidraw(tmp_path / "simple.excalidraw")
    r = choose_renderer(src)
    assert r.name == "rough"


@patch("feinschliff.diagrams.renderer.RoughRenderer._available", return_value=True)
def test_choose_renderer_falls_back_to_playwright_for_freedraw(mock_avail, tmp_path):
    src = _freedraw_excalidraw(tmp_path / "freedraw.excalidraw")
    r = choose_renderer(src)
    assert r.name == "playwright"


@patch("feinschliff.diagrams.renderer.RoughRenderer._available", return_value=False)
def test_choose_renderer_skips_rough_when_unavailable(mock_avail, tmp_path):
    src = _simple_excalidraw(tmp_path / "simple.excalidraw")
    r = choose_renderer(src)
    assert r.name == "playwright"


def test_choose_renderer_raises_when_no_support(tmp_path):
    """An unsupported file type with no renderer claiming it raises RuntimeError."""
    src = tmp_path / "x.docx"
    src.write_text("data")
    # Temporarily strip the registry to force the error path.
    import feinschliff.diagrams.renderer as _mod
    original = list(_mod._REGISTRY)
    _mod._REGISTRY.clear()
    try:
        with pytest.raises(RuntimeError, match="no registered backend"):
            choose_renderer(src)
    finally:
        _mod._REGISTRY[:] = original


# ── register_renderer ─────────────────────────────────────────────────────────

def test_register_renderer_at_priority_0_places_first():
    import feinschliff.diagrams.renderer as _mod
    original = list(_mod._REGISTRY)
    sentinel = MagicMock(spec=Renderer)
    sentinel.name = "sentinel"
    sentinel.supports.return_value = True
    try:
        register_renderer(sentinel, priority=0)
        assert _mod._REGISTRY[0] is sentinel
    finally:
        _mod._REGISTRY[:] = original


def test_register_renderer_default_priority_places_first():
    import feinschliff.diagrams.renderer as _mod
    original = list(_mod._REGISTRY)
    sentinel = MagicMock(spec=Renderer)
    sentinel.name = "sentinel2"
    sentinel.supports.return_value = True
    try:
        register_renderer(sentinel)
        assert _mod._REGISTRY[0] is sentinel
    finally:
        _mod._REGISTRY[:] = original


def test_choose_renderer_uses_registered_renderer_first(tmp_path):
    """A registered renderer with supports()=True wins over the defaults."""
    import feinschliff.diagrams.renderer as _mod
    original = list(_mod._REGISTRY)
    src = tmp_path / "x.excalidraw"
    src.write_text("{}", encoding="utf-8")

    winner = MagicMock(spec=Renderer)
    winner.name = "winner"
    winner.supports.return_value = True
    try:
        register_renderer(winner, priority=0)
        r = choose_renderer(src)
        assert r.name == "winner"
    finally:
        _mod._REGISTRY[:] = original
