"""Smoke tests for the example corpus.

Every `.exc.dsl` / `.svg.dsl` under `skills/<kind>/examples/` must parse
+ expand cleanly. Render is exercised separately (Playwright/cairo path
in CI) — this just verifies the DSL surface stays valid.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from lib.diagrams import excalidraw_expand, svg_expand


def _brand_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "brands" / "feinschliff"


SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def _corpus(kind: str, suffix: str) -> list[Path]:
    base = SKILLS_DIR / kind / "examples"
    if not base.exists():
        return []
    return sorted(base.glob(f"*{suffix}"))


@pytest.mark.parametrize("path", _corpus("excalidraw", ".exc.dsl"),
                         ids=lambda p: p.name)
def test_excalidraw_example_expands(path: Path):
    # Each corpus file declares its own virtual canvas at the top; expand()
    # accepts an override directly, so we probe the canvas line and pass `raw`.
    raw = path.read_text()
    canvas_w = canvas_h = None
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("canvas "):
            w_str, h_str = s.split()[1].split("x")
            canvas_w, canvas_h = int(w_str), int(h_str)
            break
    assert canvas_w and canvas_h, f"{path.name}: missing canvas line"
    result = excalidraw_expand.expand(
        raw, brand_dir=_brand_dir(),
        canvas_override=(canvas_w, canvas_h),
    )
    assert '"type": "excalidraw"' in result, f"{path.name}: missing excalidraw header"
    assert '"elements":' in result, f"{path.name}: no elements emitted"


@pytest.mark.parametrize("path", _corpus("svg", ".svg.dsl"),
                         ids=lambda p: p.name)
def test_svg_example_expands(path: Path):
    raw = path.read_text()
    canvas_w = canvas_h = None
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("canvas "):
            w_str, h_str = s.split()[1].split("x")
            canvas_w, canvas_h = int(w_str), int(h_str)
            break
    assert canvas_w and canvas_h, f"{path.name}: missing canvas line"
    result = svg_expand.expand(
        raw, brand_dir=_brand_dir(),
        canvas_override=(canvas_w, canvas_h),
    )
    assert result.startswith("<?xml"), f"{path.name}: not valid SVG"


def test_corpus_is_non_empty():
    """Guards against the corpus directory accidentally going empty."""
    assert _corpus("excalidraw", ".exc.dsl"), "Excalidraw corpus is empty"
    assert _corpus("svg", ".svg.dsl"), "SVG corpus is empty"
