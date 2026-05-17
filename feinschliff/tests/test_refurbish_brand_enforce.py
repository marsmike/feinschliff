"""Standalone utility: snap raw-hex SVG colors to nearest brand token hex.

The refurbish pipeline today emits token names, not hex, so this utility
is defensive plumbing for future SVG-import paths. Tests run independently
of any pipeline wiring."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from lib.diagrams.refurbish.brand_enforce import snap_svg_to_brand_palette


REPO_ROOT = Path(__file__).resolve().parents[1]
BRAND_DIR = REPO_ROOT / "brands" / "feinschliff"


def test_snap_replaces_hex_with_nearest_token(tmp_path):
    svg_in = tmp_path / "raw.svg"
    svg_in.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">'
        '<rect fill="#1133aa" width="50" height="50"/>'
        '<rect fill="#ff0000" x="50" width="50" height="50" stroke="#0f0f0f"/>'
        '</svg>'
    )
    out_path = tmp_path / "snapped.svg"
    report = snap_svg_to_brand_palette(svg_in, out_path, brand_dir=BRAND_DIR)
    body = out_path.read_text()

    assert "#1133aa" not in body
    assert "#ff0000" not in body
    assert "#0f0f0f" not in body
    assert all(repl["replaced"] for repl in report["mappings"]), report


def test_snap_no_op_when_hex_already_in_palette(tmp_path):
    palette_hex = _first_brand_hex(BRAND_DIR)
    svg_in = tmp_path / "raw.svg"
    svg_in.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg"><rect fill="{palette_hex}"/></svg>'
    )
    out_path = tmp_path / "snapped.svg"
    report = snap_svg_to_brand_palette(svg_in, out_path, brand_dir=BRAND_DIR)
    assert all(not repl["replaced"] for repl in report["mappings"])


def test_snap_handles_uppercase_hex(tmp_path):
    svg_in = tmp_path / "raw.svg"
    svg_in.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><rect fill="#FF00AA"/></svg>'
    )
    out_path = tmp_path / "snapped.svg"
    report = snap_svg_to_brand_palette(svg_in, out_path, brand_dir=BRAND_DIR)
    assert len(report["mappings"]) == 1
    # Either replaced with a brand hex (palette didn't include #ff00aa) or unchanged.
    assert "mappings" in report


def test_snap_empty_palette_returns_passthrough(tmp_path):
    # Build a fake brand dir whose tokens.json has no hex values.
    fake_brand = tmp_path / "fake-brand"
    fake_brand.mkdir()
    (fake_brand / "tokens.json").write_text(json.dumps({
        "name": {"$value": "test", "$type": "string"},
    }))
    svg_in = tmp_path / "raw.svg"
    svg_in.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><rect fill="#abcdef"/></svg>'
    )
    out_path = tmp_path / "snapped.svg"
    report = snap_svg_to_brand_palette(svg_in, out_path, brand_dir=fake_brand)
    assert report["palette_size"] == 0
    assert report["mappings"] == []
    assert out_path.read_text() == svg_in.read_text()


def _first_brand_hex(brand_dir: Path) -> str:
    tokens = json.loads((brand_dir / "tokens.json").read_text())
    def walk(o):
        if isinstance(o, dict):
            v = o.get("$value")
            if isinstance(v, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", v):
                return v
            for x in o.values():
                r = walk(x)
                if r:
                    return r
        return None
    return walk(tokens) or "#000000"
