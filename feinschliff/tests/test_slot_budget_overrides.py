"""feinschliff/tests/test_slot_budget_overrides.py

The budget gate must model the SAME size/weight the emitter renders —
decompiled packs override `size:` on nearly every node (root cause R1 of
the silent World Cup overflows)."""
from feinschliff.dsl.parser import parse_lines
from feinschliff.slot_budget import compute_slot_budgets
from feinschmiede.dsl.tokens import Tokens

RAW_12IN = {
    "color": {"ink": "#000000", "paper": "#FFFFFF", "graphite": "#444444"},
    "font-family": {"display": ["Open Sans"], "body": ["Open Sans"]},
    "font-size": {"body": "16px"},
    "font-weight": {"regular": 400, "bold": 700},
    "slide": {"width_emu": 10969625, "height_emu": 6170613,
              "width": 1920, "height": 1080},
}


def _budgets(line: str, raw=None):
    tokens = Tokens.from_dict(dict(raw or RAW_12IN), brand_name="t")
    nodes, _ = parse_lines(f"canvas 1920x1080\n{line}", source="<test>")
    return compute_slot_budgets(nodes, tokens)


def test_size_pt_override_lands_exactly_in_budget():
    """`size:16pt` on a 12in deck → the budget models exactly 16pt
    (pre-fix: style bundle 16px × 0.44987 = 7.2pt — wildly over-permissive)."""
    b = _budgets('text 100,100 "{{ t }}" style:body size:16pt maxwidth:920 maxheight:787')["t"]
    assert abs(b.size_pt - 16.0) < 1e-6
    assert abs(b.size_px - 16.0 / b.px_to_pt) < 1e-6


def test_size_px_override_lands_in_budget():
    b = _budgets('text 100,100 "{{ t }}" style:body size:56px maxwidth:800')["t"]
    assert b.size_px == 56.0


def test_weight_override_sets_bold():
    b = _budgets('text 100,100 "{{ t }}" style:body weight:bold maxwidth:800')["t"]
    assert b.bold is True


def test_no_override_unchanged_legacy():
    """Repo-brand layouts without node overrides: budget identical to before."""
    raw = {k: v for k, v in RAW_12IN.items() if k != "slide"}
    b = _budgets('text 100,100 "{{ t }}" style:body maxwidth:800 maxheight:200', raw)["t"]
    assert b.size_px == 16.0
    assert b.size_pt == 8.0       # 16px × legacy 0.5
    assert b.width_emu == int(800 * 6350)
