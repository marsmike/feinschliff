from __future__ import annotations

import json
from pathlib import Path

import pytest

from feinschliff_builder.eval.checks import CheckContext, run_check

BRAND_DIR = Path(__file__).resolve().parents[2] / "feinschliff" / "brands" / "feinschliff"


def _ctx() -> CheckContext:
    return CheckContext(brand_dir=BRAND_DIR)


def _write(tmp_path: Path, name: str, doc: dict) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(doc))
    return p


# A structurally valid minimal excalidraw doc (mirrors feinbild's own _GOOD fixture).
_VALID = {
    "type": "excalidraw", "version": 2, "appState": {},
    "elements": [
        {"id": "a", "type": "rectangle", "x": 0, "y": 0, "width": 300, "height": 120},
        {"id": "t", "type": "text", "containerId": "a", "text": "OK",
         "fontSize": 16, "x": 10, "y": 40, "width": 280, "height": 40},
    ],
}

# A doc with exactly 5 rectangles + 4 arrows (positions irrelevant to count checks).
_FIVE_FOUR = {
    "type": "excalidraw", "version": 2, "appState": {},
    "elements": (
        [{"id": f"r{i}", "type": "rectangle", "x": i * 100, "y": 0, "width": 80, "height": 60}
         for i in range(5)]
        + [{"id": f"a{i}", "type": "arrow", "x": 0, "y": 0, "width": 10, "height": 0,
            "points": [[0, 0], [10, 0]]} for i in range(4)]
    ),
}


def test_count_rectangles_equals(tmp_path):
    p = _write(tmp_path, "c.excalidraw", _FIVE_FOUR)
    assert run_check("rectangles==5", p, _ctx()) is True
    assert run_check("rectangles==4", p, _ctx()) is False


def test_count_arrows_gte(tmp_path):
    p = _write(tmp_path, "c.excalidraw", _FIVE_FOUR)
    assert run_check("arrows>=4", p, _ctx()) is True
    assert run_check("arrows>=5", p, _ctx()) is False


def test_valid_excalidraw_json(tmp_path):
    good = _write(tmp_path, "ok.excalidraw", _VALID)
    assert run_check("valid-excalidraw-json", good, _ctx()) is True
    bad = tmp_path / "bad.excalidraw"
    bad.write_text("{ not json")
    assert run_check("valid-excalidraw-json", bad, _ctx()) is False


def test_svg_viewbox_and_valid(tmp_path):
    svg = tmp_path / "ok.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
        'width="100" height="100"><rect x="1" y="1" width="10" height="10" fill="#000000"/></svg>'
    )
    assert run_check("has-viewBox", svg, _ctx()) is True
    assert run_check("valid-svg", svg, _ctx()) is True
    no_vb = tmp_path / "novb.svg"
    no_vb.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"></svg>')
    assert run_check("has-viewBox", no_vb, _ctx()) is False


def test_uses_semantic_colors(tmp_path):
    from feinschmiede.diagrams.brand_bridge import resolve

    good_hex = resolve("accent", BRAND_DIR)
    good = tmp_path / "good.svg"
    good.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        f'<rect x="1" y="1" width="5" height="5" fill="{good_hex}"/></svg>'
    )
    assert run_check("uses-semantic-colors", good, _ctx()) is True

    bad = tmp_path / "bad.svg"
    bad.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        '<rect x="1" y="1" width="5" height="5" fill="#010203"/></svg>'
    )
    assert run_check("uses-semantic-colors", bad, _ctx()) is False


def test_unknown_check_raises(tmp_path):
    p = _write(tmp_path, "c.excalidraw", _VALID)
    with pytest.raises(ValueError):
        run_check("nonsense-check", p, _ctx())
