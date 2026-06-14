"""Rough-render font substitution: brand faces replace the Excalidraw font
enums at render time (F3) — JSON stays upstream-valid, the PNG gets the
brand typography."""
import json

import pytest

from feinschmiede.diagrams.brand_bridge import BrandFonts
from feinschmiede.diagrams.render_rough import _font_family_name

_FONTS = BrandFonts(body=("Noto Sans", "Arial", "sans-serif"),
                    mono=("Noto Sans Mono", "monospace"))


def test_enum_maps_to_brand_faces():
    assert _font_family_name(2, _FONTS) == "'Noto Sans', Arial, sans-serif"
    assert _font_family_name(3, _FONTS) == "'Noto Sans Mono', monospace"
    # Hand-drawn (1) keeps the Excalidraw look — brands don't override it.
    assert "Virgil" in _font_family_name(1, _FONTS)


def test_enum_without_brand_keeps_defaults():
    assert _font_family_name(2, None) == "Helvetica, Arial, sans-serif"
    assert _font_family_name(3, None) == "Cascadia, monospace"
    assert _font_family_name(None, None) == "Helvetica, Arial, sans-serif"


def test_render_excalidraw_embeds_brand_face(tmp_path):
    cairosvg = pytest.importorskip("cairosvg")
    brand = tmp_path / "brandx"
    brand.mkdir()
    (brand / "tokens.json").write_text(json.dumps({
        "color": {"ink": {"$value": "#000000"}},
        "font-family": {"body": {"$value": ["DejaVu Sans", "sans-serif"]}},
    }), encoding="utf-8")
    doc = {
        "type": "excalidraw", "version": 2, "source": "test",
        "elements": [{
            "id": "t1", "type": "text", "x": 10, "y": 10, "width": 200,
            "height": 25, "angle": 0, "text": "Hello", "fontSize": 16,
            "fontFamily": 2, "textAlign": "left", "verticalAlign": "top",
            "strokeColor": "#000000", "backgroundColor": "transparent",
            "fillStyle": "solid", "strokeWidth": 1, "roughness": 0,
            "opacity": 100, "groupIds": [], "seed": 1,
        }],
        "appState": {"viewBackgroundColor": "#ffffff"},
    }
    src = tmp_path / "d.excalidraw"
    src.write_text(json.dumps(doc), encoding="utf-8")
    out = tmp_path / "d.png"

    from feinschmiede.diagrams import render_rough
    captured: dict = {}
    _orig = cairosvg.svg2png

    def _spy(*args, **kwargs):
        captured["svg"] = kwargs.get("bytestring", b"").decode("utf-8")
        return _orig(*args, **kwargs)

    cairosvg.svg2png = _spy
    try:
        render_rough.render_excalidraw(src, out, style="clean", brand_dir=brand)
    finally:
        cairosvg.svg2png = _orig
    assert out.exists() and out.stat().st_size > 0
    assert "'DejaVu Sans'" in captured["svg"]


def test_render_dispatcher_threads_brand_dir(tmp_path, monkeypatch):
    """render(src, out, brand_dir=...) reaches the rough renderer."""
    from feinschmiede.diagrams import render as render_mod
    seen = {}

    def _fake_rough(src, out, style="clean", brand_dir=None):
        seen["brand_dir"] = brand_dir
        out.write_bytes(b"png")
        return out

    import feinschmiede.diagrams.render_rough as rr
    monkeypatch.setattr(rr, "render_excalidraw", _fake_rough)
    src = tmp_path / "d.excalidraw"
    src.write_text(json.dumps({"type": "excalidraw", "version": 2,
                               "elements": [], "appState": {}}), encoding="utf-8")
    render_mod.render(src, tmp_path / "d.png", brand_dir=tmp_path / "b")
    assert seen["brand_dir"] == tmp_path / "b"
