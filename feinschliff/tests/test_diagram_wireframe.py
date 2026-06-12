from __future__ import annotations

from pathlib import Path

from feinschmiede.diagrams.diagram_wireframe import primitives_from_svg_dsl, primitives_from_excalidraw_dsl
from feinschmiede.diagrams.text_metrics import CHAR_WIDTH_EM, SVG_TEXT_SIZES, EXCALIDRAW_TEXT_SIZES, char_width_em_for
from feinschmiede.diagrams.brand_bridge import resolve_fonts


def _brand_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "brands" / "feinschliff"


def _brand_char_em() -> float:
    """Measured char-width ratio for the feinschliff brand's body face (F4).

    When Noto Sans is installed, this returns the measured ratio (~0.566);
    when the kill-switch is set or the font is absent, it falls back to
    CHAR_WIDTH_EM (0.62). Tests use this helper so they track the actual
    wireframe behavior rather than pinning the heuristic constant.
    """
    primary = resolve_fonts(_brand_dir()).primary_body
    return char_width_em_for(primary)


def test_svg_dsl_yields_bbox_primitives():
    dsl = """
canvas 600x400
rect bg 0,0 600x400 paper
bar b1 100,100 80x200 primary value:"$85k"
text t1 300,30 title "Q1 Revenue"
"""
    prims = primitives_from_svg_dsl(dsl, _brand_dir())
    kinds = [p.kind for p in prims]
    assert "rect" in kinds
    assert "text" in kinds
    assert kinds.count("rect") >= 2  # bg + bar


def test_excalidraw_dsl_yields_bbox_primitives():
    dsl = """
canvas 800x600
box api 100,100 200x80 "API"
box svc 400,100 200x80 "Service"
arrow api -> svc
"""
    prims = primitives_from_excalidraw_dsl(dsl, _brand_dir())
    kinds = [p.kind for p in prims]
    assert kinds.count("rect") == 2
    assert "text" in kinds
    assert "line" in kinds


# ---------------------------------------------------------------------------
# Text-width formula: size * char_width_em_for(brand_face) * len(longest_line)
# ---------------------------------------------------------------------------

def test_svg_text_width_uses_char_width_em():
    """SVG text primitive width must equal int(size * char_em * len(text)).

    SVG title = 22 px at scale=1, text="Hello" (len=5).
    With Noto Sans installed: char_em ≈ 0.566 → int(22 * 0.566 * 5) = 62.
    With heuristic fallback (0.62): int(22 * 0.62 * 5) = int(68.2) = 68.
    Test uses _brand_char_em() so it tracks the actual wireframe behavior (F4).
    """
    text = "Hello"
    level = "title"
    size = SVG_TEXT_SIZES[level]  # 22
    char_em = _brand_char_em()
    expected_w = int(size * char_em * len(text))
    dsl = f'text t1 100,100 {level} "{text}"'
    prims = primitives_from_svg_dsl(dsl, _brand_dir())
    text_prim = next(p for p in prims if p.kind == "text")
    assert text_prim.w == expected_w, (
        f"SVG text width {text_prim.w} != expected {expected_w} "
        f"(size={size}, char_em={char_em}, len={len(text)})"
    )


def test_excalidraw_text_width_uses_char_width_em():
    """Excalidraw text primitive width must equal int(size * char_em * len(text)).

    Excalidraw title = 28 px at scale=1, text="Hello" (len=5).
    With Noto Sans installed: char_em ≈ 0.566 → int(28 * 0.566 * 5) = 79.
    With heuristic fallback (0.62): int(28 * 0.62 * 5) = int(86.8) = 86.
    Test uses _brand_char_em() so it tracks the actual wireframe behavior (F4).
    """
    text = "Hello"
    level = "title"
    size = EXCALIDRAW_TEXT_SIZES[level]  # 28
    char_em = _brand_char_em()
    expected_w = int(size * char_em * len(text))
    dsl = f'text t1 100,100 "{text}" size:{level}'
    prims = primitives_from_excalidraw_dsl(dsl, _brand_dir())
    text_prim = next(p for p in prims if p.kind == "text")
    assert text_prim.w == expected_w, (
        f"Excalidraw text width {text_prim.w} != expected {expected_w} "
        f"(size={size}, char_em={char_em}, len={len(text)})"
    )


def test_svg_text_width_scales_with_canvas():
    """At 4x canvas (6880 vs baseline 1720), SVG text width must scale 4x.

    SVG title = 22px * 4.0 = 88px effective size, text="Hello" (len=5).
    With Noto Sans: int(88.0 * 0.566 * 5) = 249.
    With heuristic (0.62): int(88.0 * 0.62 * 5) = int(272.8) = 272.
    Test uses _brand_char_em() so it tracks the actual wireframe behavior (F4).
    """
    text = "Hello"
    level = "title"
    size_4x = SVG_TEXT_SIZES[level] * 4.0  # 88.0
    char_em = _brand_char_em()
    expected_w = int(size_4x * char_em * len(text))
    dsl = f'text t1 100,100 {level} "{text}"'
    prims = primitives_from_svg_dsl(dsl, _brand_dir(), canvas_w=6880)
    text_prim = next(p for p in prims if p.kind == "text")
    assert text_prim.w == expected_w, (
        f"SVG text width at 4x canvas {text_prim.w} != expected {expected_w}"
    )


def test_svg_text_multiline_uses_longest_line():
    r"""Multi-line SVG text: width is based on the longest line only.

    The DSL uses literal \n (backslash-n) inside a quoted label.  After
    shlex.split the content string is 'Hi\nthere' (9 chars with a literal
    backslash, not a newline).  The wireframe splits on that 2-char sequence
    to find the longest line — matching how excalidraw_expand converts \\n
    before passing text to the renderer.

    Longest line = "there" (len=5), SVG body = 14px, scale=1.
    With Noto Sans: int(14 * 0.566 * 5) = 39.
    With heuristic (0.62): int(14 * 0.62 * 5) = int(43.4) = 43.
    Test uses _brand_char_em() so it tracks the actual wireframe behavior (F4).
    """
    level = "body"
    size = SVG_TEXT_SIZES[level]  # 14
    # The DSL label contains a literal backslash-n (raw \n, not a newline).
    # After shlex.split this yields the Python string r'Hi\nthere'.
    raw_label = r"Hi\nthere"  # repr: 'Hi\\nthere'
    lines = raw_label.split("\\n")  # ['Hi', 'there']
    longest = max(len(line) for line in lines)  # 5
    char_em = _brand_char_em()
    expected_w = int(size * char_em * longest)
    # Embed raw label in DSL (the shlex string keeps the backslash).
    dsl = r'text t1 100,100 body "Hi\nthere"'
    prims = primitives_from_svg_dsl(dsl, _brand_dir())
    text_prim = next(p for p in prims if p.kind == "text")
    assert text_prim.w == expected_w, (
        f"SVG multiline text width {text_prim.w} != expected {expected_w} "
        f"(longest_line=5, size={size}, char_em={char_em})"
    )
