"""Semi-opaque text must blend toward the brand paper color (background),
not unconditionally toward white — on dark paper that inverts the intent."""
from feinschmiede.dsl.tokens import Tokens
from feinschliff.dsl.parser import parse_lines
from feinschliff.dsl.pptx_emit import build_presentation


def _run_color(paper_hex):
    ink = "#FFFFFF" if paper_hex == "#000000" else "#000000"
    raw = {
        "color": {"ink": ink, "paper": paper_hex, "graphite": "#444444"},
        "font-family": {"display": ["Open Sans"], "body": ["Open Sans"]},
        "font-size": {"body": "32px"},
        "font-weight": {"regular": 400},
        "style": {"body": {"font": "body", "size": "body",
                           "weight": "regular", "color": "ink",
                           "opacity": 0.5}},
    }
    nodes, _ = parse_lines('text 100,100 "Hi" style:body maxwidth:800',
                           source="<test>")
    prs = build_presentation(nodes, Tokens.from_dict(raw, brand_name="t"))
    tb = [s for s in prs.slides[0].shapes if s.has_text_frame][0]
    return str(tb.text_frame.paragraphs[0].runs[0].font.color.rgb)


def test_opacity_on_light_paper_blends_toward_white():
    assert _run_color("#FFFFFF") == "808080"   # 50% black on white — unchanged behavior


def test_opacity_on_dark_paper_blends_toward_black():
    # white ink at 50% on black paper must get DARKER (toward paper), not stay white
    assert _run_color("#000000") == "808080"
