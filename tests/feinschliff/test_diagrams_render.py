from __future__ import annotations


import pytest

from feinschmiede.diagrams.render import render


def test_render_svg_produces_png(tmp_path):
    try:
        pytest.importorskip("cairosvg")
    except OSError as exc:
        pytest.skip(f"cairosvg native library unavailable: {exc}")
    svg = (
        '<?xml version="1.0"?>'
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
        'width="100" height="100"><rect width="100" height="100" fill="#ff0000"/></svg>'
    )
    src = tmp_path / "a.svg"
    src.write_text(svg)
    out = tmp_path / "a.png"
    render(src, out)
    assert out.exists()
    assert out.stat().st_size > 100


def test_render_unknown_format_raises(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("nope")
    with pytest.raises(ValueError, match="unsupported format"):
        render(src, tmp_path / "a.png")
