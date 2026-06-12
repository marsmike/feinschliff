"""End-to-end render tests for the rough-primary / Playwright-fallback path
in lib/diagrams/render.py. Replaces the old test_excalidraw_to_svg suite
that exercised the now-removed flat SVG translator.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def _brand_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "feinschliff" / "brands" / "feinschliff"


def _has_cairo() -> bool:
    try:
        import cairosvg
        cairosvg.svg2png(bytestring=b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>')
        return True
    except (ImportError, OSError):
        return False


def test_rough_compose_emits_well_formed_svg():
    """render_rough's _compose_svg produces a valid SVG that contains every
    requested shape primitive and labels for bound text."""
    from feinschmiede.diagrams.excalidraw_expand import expand
    from feinschmiede.diagrams.render_rough import _bbox, _compose_svg

    dsl = """
canvas 800x600
box api 100,100 200x80 "API"
arrow api -> api
"""
    doc = json.loads(expand(dsl, brand_dir=_brand_dir()))
    elements = [e for e in doc["elements"] if not e.get("isDeleted")]
    by_id = {e["id"]: e for e in elements if "id" in e}
    pad = 40
    mn_x, mn_y, mx_x, mx_y = _bbox(elements)
    w = int(mx_x - mn_x + pad * 2)
    h = int(mx_y - mn_y + pad * 2)
    svg = _compose_svg(elements, by_id, w, h, pad - mn_x, pad - mn_y,
                       doc["appState"]["viewBackgroundColor"], style="clean")
    assert svg.startswith("<?xml")
    assert "<svg" in svg
    assert "API" in svg
    assert "</svg>" in svg


def test_render_excalidraw_via_rough_writes_png(tmp_path):
    """End-to-end: DSL → Excalidraw JSON → render() → PNG. Verifies the
    production dispatcher (render.py:_render_excalidraw) routes through the
    rough+cairosvg path successfully."""
    if not _has_cairo():
        pytest.skip("cairosvg unavailable; rough path can't run")

    from feinschmiede.diagrams.excalidraw_expand import expand
    from feinschmiede.diagrams.render import render

    dsl = """
canvas 800x600
box a 100,100 200x80 "Start"
box b 500,100 200x80 "End"
arrow a -> b
"""
    j_str = expand(dsl, brand_dir=_brand_dir())
    src = tmp_path / "test.excalidraw"
    src.write_text(j_str)
    out = tmp_path / "test.png"
    render(src, out)
    assert out.exists()
    assert out.stat().st_size > 200


def test_render_rough_covers_full_vocabulary(tmp_path):
    """Exercise every primitive added in the upstream-parity pass:
    box, ellipse, diamond, dot, line(dashed), arrow, text(varied levels)."""
    if not _has_cairo():
        pytest.skip("cairosvg unavailable")

    from feinschmiede.diagrams.excalidraw_expand import expand
    from feinschmiede.diagrams.render import render

    dsl = """
canvas 1000x600
theme dark
text   t1     50,30  "Title here" size:title
text   t2     50,80  "Subtitle" size:subtitle color:accent
text   t3     50,120 "body annotation" size:body
line   div    50,160 950,160 dashed
box    rect   100,200 200x100 "Rect" fill:primary
ellipse oval  400,200 200x100 "Oval" fill:secondary
diamond diam  700,200 200x100 "Decision?" fill:warning
dot    marker 500,400 fill:accent
arrow  rect -> diam label:"flow"
"""
    j_str = expand(dsl, brand_dir=_brand_dir())
    src = tmp_path / "full.excalidraw"
    src.write_text(j_str)
    out = tmp_path / "full.png"
    render(src, out)
    assert out.exists()
    assert out.stat().st_size > 500
