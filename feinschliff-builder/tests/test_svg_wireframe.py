"""Unit tests for lib/dsl/svg_wireframe — SVG wireframe renderer."""
from __future__ import annotations

import base64
from pathlib import Path

import pytest

from feinschliff.dsl.parser import DSLNode, parse_file
from feinschliff.dsl.tokens import load_tokens
from feinschliff_builder.decompile.wireframe import render_wireframe, render_wireframe_sheet

# Minimal valid 1×1 white PNG (verified bytes for a 1×1 RGB PNG).
_PNG_1X1_B64 = base64.b64encode(
    b'\x89PNG\r\n\x1a\n'
    b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x02\x00\x00\x00\x90wS\xde'
    b'\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N'
    b'\x00\x00\x00\x00IEND\xaeB`\x82'
).decode("ascii")


REPO_ROOT = Path(__file__).resolve().parents[2] / "feinschliff"
BRANDS_DIR = REPO_ROOT / "brands"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tokens():
    return load_tokens(BRANDS_DIR / "feinschliff", brands_dir=BRANDS_DIR)


def _text(label: str, xy: str = "100,100", style: str = "body",
          maxwidth: str = "760", maxheight: str | None = None) -> DSLNode:
    kw = {"style": style, "maxwidth": maxwidth}
    if maxheight:
        kw["maxheight"] = maxheight
    return DSLNode(kind="text", pos_args=[xy], kw_args=kw, label=label)


def _rect(xy: str = "0,0", wh: str = "1920x100", fill: str = "accent") -> DSLNode:
    return DSLNode(kind="rect", pos_args=[xy, wh], kw_args={"fill": fill})


def _picture(xy: str = "100,200", wh: str = "400x300", slot: str = "hero") -> DSLNode:
    return DSLNode(kind="picture", pos_args=[xy, wh], kw_args={"slot": slot})


def _line(xy1: str = "0,0", xy2: str = "100,100") -> DSLNode:
    return DSLNode(kind="line", pos_args=[xy1, xy2], kw_args={})


# ---------------------------------------------------------------------------
# render_wireframe — basic structure
# ---------------------------------------------------------------------------

def test_render_wireframe_returns_string():
    svg = render_wireframe([], _tokens())
    assert isinstance(svg, str)


def test_render_wireframe_valid_svg_root():
    """Output starts with <svg and ends with </svg>."""
    svg = render_wireframe([], _tokens())
    assert svg.strip().startswith("<svg")
    assert svg.strip().endswith("</svg>")


def test_render_wireframe_has_viewbox():
    """SVG uses a viewBox for resolution-independent scaling."""
    svg = render_wireframe([], _tokens())
    assert 'viewBox="0 0 1920 1080"' in svg


def test_render_wireframe_default_display_size():
    """Default display size is 960×540."""
    svg = render_wireframe([], _tokens())
    assert 'width="960"' in svg
    assert 'height="540"' in svg


def test_render_wireframe_custom_display_size():
    """Custom display_w / display_h override the defaults."""
    svg = render_wireframe([], _tokens(), display_w=480, display_h=270)
    assert 'width="480"' in svg
    assert 'height="270"' in svg


def test_render_wireframe_title_appears():
    """Title string is embedded in the SVG when provided."""
    svg = render_wireframe([], _tokens(), title="executive-summary")
    assert "executive-summary" in svg


def test_render_wireframe_no_title_by_default():
    """No title text node emitted when title='' (default)."""
    svg = render_wireframe([], _tokens())
    # The title element uses y="30"; no other element in an empty wireframe has that position.
    assert 'y="30"' not in svg, "title element should not appear when title=''"


def test_render_wireframe_has_background_rect():
    """Without overlay PNG, a background fill rect is present."""
    svg = render_wireframe([], _tokens())
    assert "<rect" in svg
    assert "#f9fafb" in svg


def test_render_wireframe_has_legend():
    """Output contains the legend labels."""
    svg = render_wireframe([], _tokens())
    assert "text slot" in svg
    assert "image slot" in svg
    assert "rect" in svg


# ---------------------------------------------------------------------------
# Text nodes
# ---------------------------------------------------------------------------

def test_text_node_slot_label_rendered():
    """Slot name from {{ }} placeholder appears in SVG text."""
    nodes = [_text("{{ action_title }}", maxwidth="1200")]
    svg = render_wireframe(nodes, _tokens())
    assert "action_title" in svg


def test_text_node_amber_color():
    """Text boxes use the amber stroke color."""
    nodes = [_text("{{ body }}", maxwidth="760")]
    svg = render_wireframe(nodes, _tokens())
    assert "#f59e0b" in svg


def test_text_node_no_maxwidth_draws_marker():
    """Text node without maxwidth draws a circle marker instead of a box."""
    node = DSLNode(kind="text", pos_args=["100,100"], kw_args={"style": "body"},
                   label="{{ body }}")
    svg = render_wireframe([node], _tokens())
    assert "<circle" in svg


def test_text_node_multi_slot_label():
    """Multi-slot labels ({{ a }} and {{ b }}) are concatenated."""
    nodes = [_text("{{ first }} + {{ second }}", maxwidth="760")]
    svg = render_wireframe(nodes, _tokens())
    assert "first" in svg
    assert "second" in svg


def test_text_node_static_label_shown():
    """Non-slot labels (no {{ }}) still render with the raw text."""
    nodes = [_text("Feinschliff 2026", maxwidth="400")]
    svg = render_wireframe(nodes, _tokens())
    assert "Feinschliff 2026" in svg


# ---------------------------------------------------------------------------
# Picture nodes
# ---------------------------------------------------------------------------

def test_picture_node_blue_color():
    """Picture slots use the blue stroke color."""
    nodes = [_picture()]
    svg = render_wireframe(nodes, _tokens())
    assert "#3b82f6" in svg


def test_picture_node_diagonal_x():
    """Picture nodes render with two diagonal lines (X pattern)."""
    nodes = [_picture()]
    svg = render_wireframe(nodes, _tokens())
    # Two <line> elements for the diagonals.
    assert svg.count("<line") >= 2


def test_picture_node_slot_label():
    """Slot name from kw_args['slot'] appears in the SVG."""
    nodes = [_picture(slot="hero_image")]
    svg = render_wireframe(nodes, _tokens())
    assert "hero_image" in svg


# ---------------------------------------------------------------------------
# Rect nodes
# ---------------------------------------------------------------------------

def test_rect_node_dashed_outline():
    """Rect primitives are drawn with a dashed outline."""
    nodes = [_rect()]
    svg = render_wireframe(nodes, _tokens())
    assert "stroke-dasharray" in svg


def test_rect_node_no_solid_fill():
    """Rect primitives have no solid fill (structural background only)."""
    nodes = [_rect()]
    svg = render_wireframe(nodes, _tokens())
    assert 'fill="none"' in svg or 'fill-opacity="0"' in svg or 'fill-opacity="0.07"' in svg


# ---------------------------------------------------------------------------
# Line nodes
# ---------------------------------------------------------------------------

def test_line_node_rendered():
    """Line primitives produce a <line> element."""
    nodes = [_line("0,540", "1920,540")]
    svg = render_wireframe(nodes, _tokens())
    assert "<line" in svg


# ---------------------------------------------------------------------------
# Overlay mode
# ---------------------------------------------------------------------------

def test_overlay_embeds_background_image():
    """When background_png_b64 is provided, an <image> tag is present."""
    fake_b64 = _PNG_1X1_B64
    svg = render_wireframe([], _tokens(), background_png_b64=fake_b64)
    assert "<image" in svg
    assert "data:image/png;base64," in svg


def test_overlay_opacity_in_svg():
    """Custom background_opacity value appears in the image tag."""
    fake_b64 = "iVBORw0KGgo="
    svg = render_wireframe([], _tokens(), background_png_b64=fake_b64,
                           background_opacity=0.30)
    assert 'opacity="0.30"' in svg


def test_no_background_rect_when_overlay():
    """When overlay is active, the plain background fill rect is omitted."""
    fake_b64 = "iVBORw0KGgo="
    svg = render_wireframe([], _tokens(), background_png_b64=fake_b64)
    assert "#f9fafb" not in svg


# ---------------------------------------------------------------------------
# Render order: rects behind text/picture
# ---------------------------------------------------------------------------

def test_rect_rendered_before_text():
    """Rect elements appear before text elements (background-first order)."""
    nodes = [_text("{{ title }}", maxwidth="760"), _rect()]
    svg = render_wireframe(nodes, _tokens())
    rect_pos = svg.find("stroke-dasharray")
    text_amber = svg.find("#f59e0b")
    assert rect_pos < text_amber, "rect should be rendered before text overlay"


# ---------------------------------------------------------------------------
# render_wireframe_sheet
# ---------------------------------------------------------------------------

def test_wireframe_sheet_empty_returns_svg():
    """Empty slides list → minimal valid SVG."""
    svg = render_wireframe_sheet([])
    assert "<svg" in svg


def test_wireframe_sheet_single_slide():
    """Single slide → SVG containing the slide's slot labels."""
    nodes = [_text("{{ action_title }}", maxwidth="1200")]
    slides = [(nodes, _tokens(), "my-layout")]
    svg = render_wireframe_sheet(slides)
    assert "action_title" in svg
    assert "my-layout" in svg


def test_wireframe_sheet_multiple_slides():
    """Multiple slides are all included in the sheet."""
    slides = [
        ([_text("{{ title }}", maxwidth="760")], _tokens(), "slide-1"),
        ([_text("{{ body }}", maxwidth="760")], _tokens(), "slide-2"),
        ([_picture()], _tokens(), "slide-3"),
    ]
    svg = render_wireframe_sheet(slides)
    assert "slide-1" in svg
    assert "slide-2" in svg
    assert "slide-3" in svg
    assert "title" in svg
    assert "hero" in svg


def test_wireframe_sheet_slide_count_in_header():
    """Sheet SVG mentions the slide count."""
    slides = [([], _tokens(), f"s{i}") for i in range(5)]
    svg = render_wireframe_sheet(slides)
    assert "5 slide" in svg


# ---------------------------------------------------------------------------
# Smoke test: real layout file
# ---------------------------------------------------------------------------

def test_real_layout_wireframe_smoke():
    """Parse executive-summary layout and render wireframe without error.

    Wireframe mode skips interpolate_nodes so {{ slot_name }} labels are
    preserved — the wireframe shows slot structure, not filled content.
    """
    from feinschliff.dsl.expander import expand_compounds, load_compounds_for_brand
    layout_path = REPO_ROOT / "layouts" / "executive-summary.slide.dsl"
    if not layout_path.is_file():
        pytest.skip("layout not present")
    brand_dir = BRANDS_DIR / "feinschliff"
    tokens = _tokens()
    compounds = load_compounds_for_brand(brand_dir, std_dir=REPO_ROOT / "compounds",
                                         brands_dir=BRANDS_DIR)
    nodes, cds = parse_file(layout_path)
    for cd in cds:
        compounds[cd.name] = cd
    # Skip interpolation — wireframe renders slot structure, not filled content.
    primitives, _ = expand_compounds(nodes, compounds)
    svg = render_wireframe(primitives, tokens, title="executive-summary")
    assert svg.strip().startswith("<svg")
    assert "action_title" in svg or "summary" in svg
