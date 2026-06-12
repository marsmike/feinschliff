"""feinschliff/tests/test_autoshrink_scale.py

The autoshrink pt→px back-conversion must use the build's px→pt scale.
The old `fitted_pt * 2.0` baked the legacy 0.5 scale: on a 12in deck a
fitted 14pt re-emitted at 14×2.0=28px → 28×0.44987 = 12.6pt — silently
smaller than the computed fit."""
import pytest

from feinschliff import textfit
from feinschliff.dsl.parser import parse_lines
from feinschliff.dsl.pptx_emit import _resolve_face, build_presentation
from feinschmiede.dsl.tokens import Tokens
from feinschmiede.text import measure as _measure

_LONG_TEXT = " ".join(["Measured metrics make the predictor honest"] * 3)

RAW_12IN = {
    "color": {"ink": "#000000", "paper": "#FFFFFF", "graphite": "#444444"},
    "font-family": {"display": ["DejaVu Sans"], "body": ["DejaVu Sans"]},
    "font-size": {"body": "40px"},
    "font-weight": {"regular": 400},
    "style": {"body": {"font": "body", "size": "body",
                       "weight": "regular", "color": "ink"}},
    "slide": {"width_emu": 10969625, "height_emu": 6170613,
              "width": 1920, "height": 1080},
}


def _require_dejavu():
    if _measure.find_font_file("DejaVu Sans") is None:
        pytest.skip("DejaVu Sans not resolvable on this machine")


def test_autoshrink_emits_the_fitted_pt_on_12in_deck():
    _require_dejavu()
    tokens = Tokens.from_dict(dict(RAW_12IN), brand_name="t")
    line = ('text 100,100 "' + _LONG_TEXT + '" style:body '
            'maxwidth:460 maxheight:80 autoshrink:true')
    nodes, _ = parse_lines(f"canvas 1920x1080\n{line}", source="<test>")
    prs = build_presentation(nodes, tokens)
    tb = [s for s in prs.slides[0].shapes if s.has_text_frame][0]
    run = tb.text_frame.paragraphs[0].runs[0]

    # Recompute the expected fit exactly like the emitter does.
    # _EMU_PER_PX = width_emu / canvas_w; _PX_TO_PT = _EMU_PER_PX / EMU_PER_PT
    from feinschmiede.geometry import units as _units
    px_to_pt = _units.emu_per_px(10969625, 1920) / 12700
    emu_per_px = _units.emu_per_px(10969625, 1920)
    face, bold = _resolve_face("DejaVu Sans", 400)
    # No `padding:` kwarg → emitter uses PowerPoint OOXML defaults (in EMU)
    inset_w_emu = 91440 + 91440
    inset_h_emu = 45720 + 45720
    expected = textfit.autoshrink_size(
        _LONG_TEXT, font=face, max_size_pt=40 * px_to_pt, min_size_pt=10,
        bold=bold, width_emu=max(1, int(460 * emu_per_px) - inset_w_emu),
        height_emu=max(1, int(80 * emu_per_px) - inset_h_emu), line_height=1.2,
    )
    # _style_run calls Pt(_px_to_pt(style.size_px)) — Pt() stores exact EMU so
    # there is no rounding; tolerate only float-arithmetic epsilon.
    assert abs(run.font.size.pt - expected) < 0.01, (
        f"expected the fitted {expected}pt, got {run.font.size.pt}pt"
    )
