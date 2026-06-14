"""Tests for the virtual viewport plumbing — parser captures `virtual:WxH`,
the expander threads it to expand_diagram_blocks via canvas_override, and
the validators receive the right canvas dimensions in _diagram_meta.

These tests stub `feinschmiede.diagrams.render.render` so CI doesn't need a
rendering backend installed (the parser/expander/meta path is what we're
validating; rasterization is covered by the render-backend tests
themselves, which CI skips for the same reason)."""
from __future__ import annotations

from pathlib import Path

import pytest

from feinschliff.dsl.parser import parse_lines
from feinschliff.dsl.expander import expand_diagram_blocks


def _brand_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "feinschliff" / "brands" / "feinschliff"


@pytest.fixture(autouse=True)
def _stub_render(monkeypatch):
    """Bypass real rendering — these tests don't care about the PNG."""
    monkeypatch.setattr(
        "feinschmiede.diagrams.render.render",
        lambda src, out, **_kw: out.write_bytes(b"\x89PNG\r\n\x1a\n") or out,
    )


def test_parser_captures_virtual_dimensions():
    src = """
excalidraw d 100,300 1720x720 virtual:6880x2880 {
  box a 200,200 1000x400 "A"
}
"""
    nodes, _ = parse_lines(src)
    assert len(nodes) == 1
    n = nodes[0]
    assert n.kind == "excalidraw"
    assert n.kw_args["w"] == 1720 and n.kw_args["h"] == 720
    assert n.kw_args["virtual_w"] == 6880 and n.kw_args["virtual_h"] == 2880


def test_parser_without_virtual_omits_field():
    src = """
excalidraw d 100,300 1720x720 {
  box a 200,200 100x40 "A"
}
"""
    nodes, _ = parse_lines(src)
    n = nodes[0]
    assert "virtual_w" not in n.kw_args


def test_expander_uses_virtual_canvas_for_diagram_meta(tmp_path: Path):
    src = """
excalidraw d 100,300 1720x720 virtual:6880x2880 {
  box a 200,200 1000x400 "A"
}
"""
    nodes, _ = parse_lines(src)
    out = expand_diagram_blocks(
        nodes,
        brand_dir=_brand_dir(),
        out_dir=tmp_path,
        layout_dir=tmp_path,
        slide_index=1,
    )
    pic = out[0]
    meta = pic.kw_args["_diagram_meta"]
    assert meta["virtual_canvas_w"] == 6880
    assert meta["virtual_canvas_h"] == 2880
    assert meta["slot_w"] == 1720
    assert meta["slot_h"] == 720


def test_expander_without_virtual_meta_falls_back_to_slot(tmp_path: Path):
    src = """
excalidraw d 100,300 1720x480 {
  box a 200,100 1000x200 "A"
}
"""
    nodes, _ = parse_lines(src)
    out = expand_diagram_blocks(
        nodes,
        brand_dir=_brand_dir(),
        out_dir=tmp_path,
        layout_dir=tmp_path,
        slide_index=1,
    )
    meta = out[0].kw_args["_diagram_meta"]
    # No virtual → virtual_canvas_w == slot_w
    assert meta["virtual_canvas_w"] == 1720
    assert meta["slot_w"] == 1720


def test_virtual_in_cache_key_prevents_collision(tmp_path: Path):
    """Identical body + slot + brand but different virtual dimensions
    must produce different artifact filenames."""
    src1 = """
excalidraw d 100,300 1720x720 virtual:3440x960 {
  box a 200,200 400x200 "A"
}
"""
    src2 = """
excalidraw d 100,300 1720x720 virtual:6880x2880 {
  box a 200,200 400x200 "A"
}
"""
    nodes1, _ = parse_lines(src1)
    nodes2, _ = parse_lines(src2)
    out1 = expand_diagram_blocks(nodes1, brand_dir=_brand_dir(),
                                  out_dir=tmp_path, layout_dir=tmp_path, slide_index=1)
    out2 = expand_diagram_blocks(nodes2, brand_dir=_brand_dir(),
                                  out_dir=tmp_path, layout_dir=tmp_path, slide_index=1)
    src_path_1 = out1[0].kw_args["src"]
    src_path_2 = out2[0].kw_args["src"]
    assert src_path_1 != src_path_2, (
        "different virtual dims must yield distinct cache keys"
    )
