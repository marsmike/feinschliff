"""First-class italic: style-bundle property + text node kwarg.

Tests verify that:
  - `italic:true` kwarg on a text node sets font.italic = True on the run
  - without the kwarg the run has font.italic = None (python-pptx inherit-from-theme)
  - a brand style bundle with `italic: true` also reaches the run font
"""
from feinschmiede.dsl.tokens import Tokens
from feinschliff.dsl.parser import parse_lines
from feinschliff.dsl.pptx_emit import build_presentation


def _minimal_raw(extra_style=None):
    raw = {
        "color": {"ink": "#000000", "paper": "#FFFFFF"},
        "font-family": {"display": ["Open Sans"], "body": ["Open Sans"]},
        "font-size": {"body": "32px"},
        "font-weight": {"regular": 400},
        "style": {
            "body": {"font": "body", "size": "body",
                     "weight": "regular", "color": "ink"},
        },
    }
    if extra_style:
        raw["style"].update(extra_style)
    return raw


def _first_run_font(dsl_source, extra_style=None):
    nodes, _ = parse_lines(dsl_source, source="<test>")
    prs = build_presentation(nodes, Tokens.from_dict(_minimal_raw(extra_style), brand_name="t"))
    tb = [s for s in prs.slides[0].shapes if s.has_text_frame][0]
    return tb.text_frame.paragraphs[0].runs[0].font


def test_text_node_italic_kwarg():
    """`italic:true` kwarg on a text node sets run font.italic to True."""
    font = _first_run_font('text 100,100 "Hi" style:body maxwidth:800 italic:true')
    assert font.italic is True


def test_text_default_italic_unset():
    """No italic kwarg → run font.italic is None (python-pptx inherit)."""
    font = _first_run_font('text 100,100 "Hi" style:body maxwidth:800')
    assert font.italic is None


def test_style_bundle_italic_reaches_run():
    """Brand style bundle with `italic: true` sets run font.italic to True,
    without any per-node kwarg."""
    extra = {
        "body": {"font": "body", "size": "body",
                 "weight": "regular", "color": "ink", "italic": True},
    }
    font = _first_run_font('text 100,100 "Hi" style:body maxwidth:800', extra_style=extra)
    assert font.italic is True
