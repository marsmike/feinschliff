"""tests/feinschliff/test_slot_budget_overrides.py

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
    """size:56px passes through unscaled."""
    b = _budgets('text 100,100 "{{ t }}" style:body size:56px maxwidth:800')["t"]
    assert b.size_px == 56.0


def test_weight_override_sets_bold():
    b = _budgets('text 100,100 "{{ t }}" style:body weight:bold maxwidth:800')["t"]
    assert b.bold is True
    b = _budgets('text 100,100 "{{ t }}" style:body weight:regular maxwidth:800')["t"]
    assert b.bold is False


def test_no_override_unchanged_legacy():
    """Repo-brand layouts without node overrides: budget identical to before."""
    raw = {k: v for k, v in RAW_12IN.items() if k != "slide"}
    b = _budgets('text 100,100 "{{ t }}" style:body maxwidth:800 maxheight:200', raw)["t"]
    assert b.size_px == 16.0
    assert b.size_pt == 8.0       # 16px × legacy 0.5
    assert b.width_emu == int(800 * 6350)


def test_budget_face_matches_emitter_when_resolvable():
    """A fontconfig-resolvable face not in textfit's ratio table must be
    modeled verbatim (real metrics) — the same face the emitter's fit
    paths use — not collapsed to the 'default' heuristic."""
    import pytest
    from feinschmiede.text import measure
    if measure.find_font_file("DejaVu Sans") is None:
        pytest.skip("DejaVu Sans not resolvable")
    raw = dict(RAW_12IN)
    raw["font-family"] = {"display": ["DejaVu Sans"], "body": ["DejaVu Sans"]}
    b = _budgets('text 100,100 "{{ t }}" style:body maxwidth:800 maxheight:200', raw)["t"]
    assert b.font_family == "DejaVu Sans"
    assert b.bold is False


def test_budget_face_falls_back_to_known_family(monkeypatch):
    """With real metrics unavailable, the legacy walk still finds the first
    ratio-table family in the fallback list — unchanged behavior."""
    from feinschmiede.text import measure
    monkeypatch.setenv("FEINSCHMIEDE_NO_REAL_METRICS", "1")
    measure.clear_caches()
    raw = dict(RAW_12IN)
    raw["font-family"] = {"display": ["NoSuchFont"], "body": ["NoSuchFont", "Open Sans"]}
    b = _budgets('text 100,100 "{{ t }}" style:body maxwidth:800 maxheight:200', raw)["t"]
    assert b.font_family == "Open Sans"
    measure.clear_caches()


def test_budget_face_table_families_unchanged():
    """Ratio-table families resolve identically to before (env-independent)."""
    raw = dict(RAW_12IN)
    raw["font-family"] = {"display": ["Open Sans"], "body": ["Open Sans"]}
    b = _budgets('text 100,100 "{{ t }}" style:body maxwidth:800 maxheight:200', raw)["t"]
    assert b.font_family == "Open Sans"


def test_autoshrink_node_rescues_moderate_overflow():
    """Content that overflows at the declared size but fits ≥10pt after
    shrinking must NOT abort the build — the emitter will rescue it (E).

    Arithmetic (validated, 12in scale emu_per_px≈5713.35):
      box 600×120px → width_emu≈3,428,007, height_emu≈685,601
      default insets (no padding kwarg): inset_w=182880, inset_h=91440
      reduced envelope: 3,245,127 × 594,161 EMU
      16pt DejaVu Sans, raw box: overflows (>2 lines).
      autoshrink_size with reduced envelope → 14pt; fits at 14pt → rescue fires, no defect.
    """
    import pytest
    from feinschliff.content_validator import validate_content
    from feinschmiede.text import measure
    if measure.find_font_file("DejaVu Sans") is None:
        pytest.skip("DejaVu Sans not resolvable")
    raw = dict(RAW_12IN)
    raw["font-family"] = {"display": ["DejaVu Sans"], "body": ["DejaVu Sans"]}
    line = ('text 100,100 "{{ t }}" style:body size:16pt autoshrink:true '
            'maxwidth:600 maxheight:120')
    b = _budgets(line, raw)["t"]
    assert b.autoshrink is True
    assert b.inset_w_emu == 182880   # default OOXML (no padding kwarg)
    assert b.inset_h_emu == 91440
    # ~3 lines at 16pt in a 2-line box: overflows declared, fits at 14pt in reduced box.
    text = "Quarterly enterprise revenue grew across all priority regions again"
    defects = validate_content({"t": text}, slot_budgets={"t": b})
    assert not [d for d in defects if d.kind == "slot-overflow"], defects


def test_autoshrink_floor_still_fatal():
    """Even the 10pt floor can't fit a paragraph in a sliver — still fatal.

    Arithmetic (validated, 12in scale emu_per_px≈5713.35):
      box 200×30px → width_emu≈1,142,669, height_emu≈171,400
      default insets: inset_w=182880, inset_h=91440
      reduced envelope: 959,789 × 79,960 EMU
      10pt line height in EMU = 10 × 1.2 × 12700 = 152,400
      reduced_h (79960) < one line (152400) → no size fits in reduced box.
      autoshrink_size returns 10pt (floor); fits at 10pt reduced → False.
      Defect is raised with "10pt" in message.
    """
    import pytest
    from feinschliff.content_validator import validate_content
    from feinschmiede.text import measure
    if measure.find_font_file("DejaVu Sans") is None:
        pytest.skip("DejaVu Sans not resolvable")
    raw = dict(RAW_12IN)
    raw["font-family"] = {"display": ["DejaVu Sans"], "body": ["DejaVu Sans"]}
    line = ('text 100,100 "{{ t }}" style:body size:16pt autoshrink:true '
            'maxwidth:200 maxheight:30')
    b = _budgets(line, raw)["t"]
    text = " ".join(["overflowing"] * 40)
    defects = validate_content({"t": text}, slot_budgets={"t": b})
    overflow = [d for d in defects if d.kind == "slot-overflow"]
    assert overflow and "10pt" in overflow[0].message


def test_autoshrink_inset_aware_catches_floor_miss():
    """The raw-rescue path silently passes content that the emitter cannot fit:
    content fits the RAW box at 10pt but NOT the inset-reduced box the emitter
    uses.  The inset-aware rescue (commit fix) must produce a floor-fatal defect.

    Arithmetic (validated, 12in scale emu_per_px≈5713.35):
      box 123×82px → raw_w≈702,741, raw_h≈468,494
      default insets (no padding kwarg): inset_w=182880, inset_h=91440
      reduced: 519,861 × 377,054 EMU
      text='overflow text here now' at 10pt:
        fits in raw  (3 lines × 152400 = 457200 ≤ 468494): True
        fits in reduced (same text → 5 lines × 152400 = 762000 > 377054): False
      Old raw-rescue would suppress (fits(10pt, raw)=True); new inset-aware rescue
      detects the real defect and produces a slot-overflow with '10pt' in message.
      Also verifies that inset_w_emu==182880 and padding:1 yields int(1*emu_per_px)*2.
    """
    import pytest
    from feinschliff.content_validator import validate_content
    from feinschmiede.text import measure
    if measure.find_font_file("DejaVu Sans") is None:
        pytest.skip("DejaVu Sans not resolvable")
    raw = dict(RAW_12IN)
    raw["font-family"] = {"display": ["DejaVu Sans"], "body": ["DejaVu Sans"]}

    # --- pin inset values for node without padding ---
    line_no_pad = ('text 100,100 "{{ t }}" style:body size:16pt autoshrink:true '
                   'maxwidth:123 maxheight:82')
    b_no_pad = _budgets(line_no_pad, raw)["t"]
    assert b_no_pad.inset_w_emu == 182880, (
        f"expected default OOXML inset_w 182880, got {b_no_pad.inset_w_emu}"
    )
    assert b_no_pad.inset_h_emu == 91440, (
        f"expected default OOXML inset_h 91440, got {b_no_pad.inset_h_emu}"
    )

    # --- pin padding:1 form (uniform 1px → int(1*emu_per_px) each side × 2) ---
    emu_per_px = RAW_12IN["slide"]["width_emu"] / 1920
    expected_pad1 = int(1 * emu_per_px) * 2   # both sides summed
    line_pad1 = ('text 100,100 "{{ t }}" style:body size:16pt autoshrink:true '
                 'maxwidth:800 maxheight:200 padding:1')
    b_pad1 = _budgets(line_pad1, raw)["t"]
    assert b_pad1.inset_w_emu == expected_pad1, (
        f"padding:1 → inset_w_emu expected {expected_pad1}, got {b_pad1.inset_w_emu}"
    )
    assert b_pad1.inset_h_emu == expected_pad1, (
        f"padding:1 → inset_h_emu expected {expected_pad1}, got {b_pad1.inset_h_emu}"
    )

    # --- floor-miss: fits raw at 10pt but NOT inset-reduced box ---
    text = "overflow text here now"
    defects = validate_content({"t": text}, slot_budgets={"t": b_no_pad})
    overflow = [d for d in defects if d.kind == "slot-overflow"]
    assert overflow, (
        "expected slot-overflow defect (inset-aware rescue should catch it); got none"
    )
    assert "10pt" in overflow[0].message, (
        f"expected '10pt' in defect message, got: {overflow[0].message!r}"
    )
