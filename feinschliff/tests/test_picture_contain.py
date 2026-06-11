"""Default (non-cover) picture placement must contain, not stretch."""
from PIL import Image
from pptx.enum.shapes import MSO_SHAPE_TYPE

from feinschmiede.dsl.tokens import Tokens
from feinschliff.dsl.parser import parse_lines
from feinschliff.dsl.pptx_emit import build_presentation

RAW = {
    "color": {
        "ink": "#000000",
        "paper": "#FFFFFF",
        "paper-2": "#EEEEEE",
        "fog": "#CCCCCC",
        "graphite": "#444444",
    },
    "font-family": {"display": ["Open Sans"], "body": ["Open Sans"]},
    "font-size": {"body": "32px"},
    "font-weight": {"regular": 400},
}


def _build(tmp_path, dsl_line):
    img = tmp_path / "wide.png"
    Image.new("RGB", (200, 100), "red").save(img)
    nodes, _ = parse_lines(dsl_line.format(img=img), source="<test>")
    tokens = Tokens.from_dict(RAW, brand_name="t")
    prs = build_presentation(nodes, tokens)
    return prs.slides[0].shapes


def test_contain_preserves_aspect_and_centers(tmp_path):
    shapes = _build(tmp_path, 'picture 100,100 400x400 path:"{img}"')
    pic = [s for s in shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE][0]
    # 2:1 source in 1:1 box -> width 400px, height 200px, y-centered
    assert pic.width == int(400 * 6350)
    assert pic.height == int(200 * 6350)
    assert pic.top == int((100 + 100) * 6350)   # 100 + (400-200)/2


def test_cover_still_fills_box(tmp_path):
    shapes = _build(tmp_path, 'picture 100,100 400x400 path:"{img}" cover:true')
    pic = [s for s in shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE][0]
    assert pic.width == int(400 * 6350)
    assert pic.height == int(400 * 6350)
