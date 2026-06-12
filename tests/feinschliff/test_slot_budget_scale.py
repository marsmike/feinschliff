"""Slot budgets must use the same px->EMU/pt scale the emitter derives from
tokens slide.width_emu — not frozen legacy constants."""
from feinschmiede.dsl.tokens import Tokens
from feinschliff.dsl.parser import parse_lines
from feinschliff.slot_budget import compute_slot_budgets

BASE_RAW = {
    "color": {"ink": "#000000", "paper": "#FFFFFF", "graphite": "#444444"},
    "font-family": {"display": ["Open Sans"], "body": ["Open Sans"]},
    "font-size": {"body": "32px"},
    "font-weight": {"regular": 400},
}

def _budget(raw):
    tokens = Tokens.from_dict(raw, brand_name="t")
    nodes, _ = parse_lines(
        'text 100,100 "{{ body }}" style:body maxwidth:800 maxheight:200',
        source="<test>",
    )
    return compute_slot_budgets(nodes, tokens)["body"]

def test_legacy_scale_when_no_width_emu():
    b = _budget(dict(BASE_RAW))
    assert b.width_emu == int(800 * 6350)
    assert b.size_pt == 16.0  # 32px * 0.5

def test_scale_follows_tokens_width_emu():
    raw = dict(BASE_RAW)
    raw["slide"] = {"width_emu": 9144000, "width": 1920, "height": 1080}  # 10in slide
    b = _budget(raw)
    emu_per_px = 9144000 / 1920          # 4762.5
    assert b.width_emu == int(800 * emu_per_px)
    assert abs(b.size_pt - 32 * (emu_per_px / 12700)) < 1e-6
