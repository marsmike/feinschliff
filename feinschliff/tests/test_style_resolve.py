"""feinschliff/tests/test_style_resolve.py

resolve_node_style must apply node-level overrides exactly like
pptx_emit._emit_text used to inline — same conversions, same precedence."""
from feinschliff.dsl.parser import parse_lines
from feinschliff.dsl.style_resolve import resolve_node_style, step_hierarchy
from feinschmiede.dsl.tokens import Tokens

RAW = {
    "color": {"ink": "#000000", "paper": "#FFFFFF", "graphite": "#444444",
              "fog": "#888888", "accent": "#FF0000"},
    "font-family": {"display": ["Open Sans"], "body": ["Open Sans"]},
    "font-size": {"body": "32px", "huge": "120px"},
    "font-weight": {"regular": 400, "bold": 700},
    "style": {"body": {"font": "body", "size": "body",
                       "weight": "regular", "color": "ink"}},
}


def _node(line: str):
    nodes, _ = parse_lines(line, source="<test>")
    return nodes[0]


def _tokens() -> Tokens:
    return Tokens.from_dict(dict(RAW), brand_name="t")


def test_no_overrides_matches_bundle():
    style = resolve_node_style(_node('text 0,0 "x" style:body'), _tokens())
    assert style.size_px == 32.0
    assert style.weight == 400
    assert style.italic is False


def test_size_pt_override_uses_px_to_pt_scale():
    # 16pt at the 12in-deck scale 0.44987 → ~35.57 design-px.
    scale = 10969625 / 1920 / 12700
    style = resolve_node_style(
        _node('text 0,0 "x" style:body size:16pt'), _tokens(), px_to_pt=scale)
    assert abs(style.size_px - 16.0 / scale) < 1e-6
    # Legacy default scale: 16pt → 32px.
    style = resolve_node_style(_node('text 0,0 "x" style:body size:16pt'), _tokens())
    assert style.size_px == 32.0


def test_size_px_and_bare_and_token_forms():
    t = _tokens()
    assert resolve_node_style(_node('text 0,0 "x" style:body size:56px'), t).size_px == 56.0
    assert resolve_node_style(_node('text 0,0 "x" style:body size:56'), t).size_px == 56.0
    assert resolve_node_style(_node('text 0,0 "x" style:body size:huge'), t).size_px == 120.0


def test_weight_color_italic_overrides():
    t = _tokens()
    style = resolve_node_style(
        _node('text 0,0 "x" style:body weight:bold color:accent italic:true'), t)
    assert style.weight == 700
    assert style.color_hex == "#FF0000"
    assert style.color_role == "accent"
    assert style.italic is True


def test_indent_steps_hierarchy():
    t = _tokens()
    base = resolve_node_style(_node('text 0,0 "x" style:body'), t)
    stepped = resolve_node_style(_node('text 0,0 "x" style:body indent:1'), t)
    exp_size, exp_weight, exp_color = step_hierarchy(
        base.size_px, base.weight, base.color_role, level=1)
    assert stepped.size_px == exp_size
    assert stepped.weight == exp_weight
    assert exp_color == "graphite"
    assert stepped.color_role == "graphite"
