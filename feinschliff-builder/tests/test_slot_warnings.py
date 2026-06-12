"""Pack-build box-sanity lint: statically impossible/narrow/overlapping slot
boxes become `slot_warnings` front-matter at decompile time — caught once
per pack, not once per deck. Geometry mirrors the World Cup incidents
(16pt label in a 27px box; two colliding chapter boxes) with NEUTRAL
synthetic content — never bsh/bosch material."""
from pathlib import Path

from feinschliff_builder.decompile.layout_profile_gen import (
    apply_profile,
    classify_layout,
)

# 12in-deck pack tokens: px_per_pt = 1920*12700/10969625 ≈ 2.2229.
_TOKENS_12IN = """\
{
  "color": {"ink": {"$value": "#000000"}, "paper": {"$value": "#FFFFFF"}},
  "font-family": {"display": {"$value": ["DejaVu Sans"]},
                  "body": {"$value": ["DejaVu Sans"]}},
  "font-size": {"body": {"$value": "16px"}},
  "font-weight": {"regular": {"$value": 400}},
  "slide": {"width_emu": {"$value": "10969625"},
            "height_emu": {"$value": "6170613"}}
}
"""


def _brand(tmp_path: Path) -> Path:
    brand = tmp_path / "brands" / "synthpack"
    (brand / "assets").mkdir(parents=True)
    (brand / "tokens.json").write_text(_TOKENS_12IN, encoding="utf-8")
    return brand


def _classify(dsl: str, brand: Path) -> dict:
    return classify_layout(
        dsl, layout_name="synth", slide_index=1, total_slides=10,
        asset_root=brand / "assets", brand_dir=brand,
    )


def test_impossible_box_flagged(tmp_path):
    """16pt on a 12in deck is ~35.6px; one 1.2-line is ~43px — a 27px-tall
    box can never show a line (the slide-30 incident class)."""
    brand = _brand(tmp_path)
    dsl = ('canvas 1920x1080\n'
           'text 100,500 size:16pt maxwidth:300 maxheight:27 '
           '"{{ text_1 | default(\\"Label\\") }}"\n')
    profile = _classify(dsl, brand)
    warnings = profile.get("slot_warnings", {})
    assert any(w.startswith("IMPOSSIBLE_BOX") for w in warnings.get("text_1", [])), warnings


def test_narrow_box_flagged(tmp_path):
    """< 8 chars per line at the resolved size → NARROW_BOX."""
    brand = _brand(tmp_path)
    dsl = ('canvas 1920x1080\n'
           'text 100,500 size:16pt maxwidth:90 maxheight:200 '
           '"{{ text_1 | default(\\"Label\\") }}"\n')
    profile = _classify(dsl, brand)
    assert any(w.startswith("NARROW_BOX")
               for w in profile.get("slot_warnings", {}).get("text_1", []))


def test_overlapping_boxes_flagged_pairwise(tmp_path):
    """Two slot boxes intersecting as drawn (the chapter-2 incident class)."""
    brand = _brand(tmp_path)
    dsl = ('canvas 1920x1080\n'
           'text 100,400 size:16pt maxwidth:800 maxheight:200 '
           '"{{ text_1 | default(\\"One\\") }}"\n'
           'text 300,450 size:16pt maxwidth:800 maxheight:200 '
           '"{{ text_2 | default(\\"Two\\") }}"\n')
    profile = _classify(dsl, brand)
    sw = profile.get("slot_warnings", {})
    assert any(w.startswith("SLOT_BOX_OVERLAP") for w in sw.get("text_1", []))
    assert any(w.startswith("SLOT_BOX_OVERLAP") for w in sw.get("text_2", []))


def test_clean_layout_has_no_warnings_key(tmp_path):
    brand = _brand(tmp_path)
    dsl = ('canvas 1920x1080\n'
           'text 100,100 size:16pt maxwidth:900 maxheight:200 '
           '"{{ text_1 | default(\\"Fine\\") }}"\n'
           'text 100,400 size:16pt maxwidth:900 maxheight:200 '
           '"{{ text_2 | default(\\"Also fine\\") }}"\n')
    profile = _classify(dsl, brand)
    assert "slot_warnings" not in profile


def test_works_without_brand_dir(tmp_path):
    """No tokens → legacy 2px/pt scale; lint still runs, nothing crashes."""
    dsl = ('canvas 1920x1080\n'
           'text 100,500 size:16pt maxwidth:300 maxheight:20 '
           '"{{ text_1 | default(\\"Label\\") }}"\n')
    profile = classify_layout(
        dsl, layout_name="synth", slide_index=1, total_slides=10,
        asset_root=tmp_path / "assets",
    )
    # 16pt × 2.0 × 1.2 = 38.4px > 20px → impossible even at legacy scale.
    assert any(w.startswith("IMPOSSIBLE_BOX")
               for w in profile.get("slot_warnings", {}).get("text_1", []))


def test_apply_profile_writes_slot_warnings(tmp_path):
    """apply_profile passes slot_warnings through to the written front-matter."""
    brand = _brand(tmp_path)
    dsl = ('canvas 1920x1080\n'
           'text 100,500 size:16pt maxwidth:300 maxheight:27 '
           '"{{ text_1 | default(\\"Label\\") }}"\n')
    profile = _classify(dsl, brand)
    assert "slot_warnings" in profile, "test pre-condition: profile must have warnings"
    result = apply_profile(dsl, profile)
    assert "slot_warnings:" in result
