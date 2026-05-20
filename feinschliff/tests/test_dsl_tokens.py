"""Unit tests for `lib.dsl.tokens`."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.dsl.tokens import load_tokens


REPO_ROOT = Path(__file__).resolve().parents[1]
BRANDS_DIR = REPO_ROOT / "brands"


# ---------------------------------------------------------------------------
# Real-repo fixtures: feinschliff (leaf, no extends) + catppuccin-macchiato
# (extends: feinschliff).
# ---------------------------------------------------------------------------

def test_load_tokens_leaf_brand_without_extends():
    """`feinschliff` has no `extends:` — its tokens.json is loaded directly."""
    tokens = load_tokens(BRANDS_DIR / "feinschliff", brands_dir=BRANDS_DIR)
    # Sanity: the brand name and the accent color round-trip from the raw json.
    assert tokens.brand_name == "feinschliff"
    raw_accent = json.loads((BRANDS_DIR / "feinschliff" / "tokens.json").read_text())
    expected = raw_accent["color"]["accent"]
    expected_value = expected["$value"] if isinstance(expected, dict) else expected
    # `Tokens.color()` unwraps the designtokens schema.
    assert tokens.color("accent").lower() == expected_value.lower()


def test_load_tokens_walks_extends_chain_child_overrides_parent():
    """catppuccin-macchiato extends feinschliff. Its `accent` overrides the
    parent, while inherited font-sizes still resolve through the parent."""
    macchiato = load_tokens(BRANDS_DIR / "catppuccin-macchiato", brands_dir=BRANDS_DIR)
    feinschliff = load_tokens(BRANDS_DIR / "feinschliff", brands_dir=BRANDS_DIR)
    # Child accent must differ from parent (child wins).
    assert macchiato.color("accent").lower() != feinschliff.color("accent").lower()
    # Child inherits font-size 'body' from parent (macchiato doesn't redefine it).
    assert macchiato.font_size_px("body") == feinschliff.font_size_px("body")


def test_color_accepts_inline_hex_literal():
    """`Tokens.color()` returns `#RRGGBB` literals unchanged so the hybrid
    decompiler's source-fidelity fallback (raw hex for shapes whose source
    colour has no close brand-token match) doesn't crash the build with
    `KeyError: no color token '#FFFFFF'`."""
    tokens = load_tokens(BRANDS_DIR / "feinschliff", brands_dir=BRANDS_DIR)
    assert tokens.color("#FFFFFF") == "#FFFFFF"
    assert tokens.color("#ffed00") == "#FFED00"   # case-normalised
    assert tokens.color("#abc") == "#AABBCC"      # 3-digit expanded


def test_color_rejects_non_hex_unknown_token():
    """Non-hex unknown names still raise KeyError — only `#…` passes through."""
    tokens = load_tokens(BRANDS_DIR / "feinschliff", brands_dir=BRANDS_DIR)
    with pytest.raises(KeyError, match="no color token 'royal-blue'"):
        tokens.color("royal-blue")


def test_load_tokens_detects_cycle(tmp_path):
    """Two brands that extend each other → ValueError."""
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "DESIGN.md").write_text("---\nextends: b\n---\n")
    (a / "tokens.json").write_text("{}")
    (b / "DESIGN.md").write_text("---\nextends: a\n---\n")
    (b / "tokens.json").write_text("{}")
    with pytest.raises(ValueError) as exc:
        load_tokens(a, brands_dir=tmp_path)
    assert "cycl" in str(exc.value).lower()


def test_load_tokens_dangling_parent_raises(tmp_path):
    """`extends: <missing>` raises FileNotFoundError with the missing name."""
    child = tmp_path / "child"
    child.mkdir()
    (child / "DESIGN.md").write_text("---\nextends: ghost-brand\n---\n")
    (child / "tokens.json").write_text("{}")
    with pytest.raises(FileNotFoundError) as exc:
        load_tokens(child, brands_dir=tmp_path)
    assert "ghost-brand" in str(exc.value)


def test_load_tokens_deep_merges_nested_maps(tmp_path):
    """Child overrides win at the leaf level; parent leaves untouched
    survive in the merged map (deep merge)."""
    parent = tmp_path / "p"
    child = tmp_path / "c"
    parent.mkdir()
    child.mkdir()
    (parent / "tokens.json").write_text(json.dumps({
        "color": {"accent": "#111111", "ink": "#000000"},
        "font-family": {"display": ["Noto Sans"], "body": ["Noto Sans"], "mono": ["Noto Sans Mono"]},
        "font-size": {"body": "20px"},
    }))
    (child / "DESIGN.md").write_text("---\nextends: p\n---\n")
    (child / "tokens.json").write_text(json.dumps({
        "color": {"accent": "#FF0000"},   # override only accent
    }))
    t = load_tokens(child, brands_dir=tmp_path)
    assert t.color("accent") == "#FF0000"          # child wins
    assert t.color("ink") == "#000000"             # parent survives
    assert t.font_size_px("body") == 20.0          # parent survives


# ---------------------------------------------------------------------------
# Layer 1 typography / picture-treatment / locale tokens (task 2).
# ---------------------------------------------------------------------------


def test_typography_display_tracking_curve_optional():
    """display_tracking_curve is optional; absence is not an error."""
    from lib.dsl.tokens import Tokens

    minimal = {
        "color": {"ink": "#111", "accent": "#f00", "paper": "#fff"},
        "font-family": {"display": ["Inter"], "body": ["Inter"], "mono": ["Consolas"]},
        "font-size": {"slide-title": "56px", "body": "18px", "eyebrow": "14px"},
        "font-weight": {"regular": 400, "semibold": 600, "bold": 700},
    }
    tokens = Tokens.from_dict(minimal, brand_name="test")
    assert tokens.display_tracking_curve == {}      # default empty mapping
    assert tokens.tnum_font is None
    assert tokens.tnum_slot_keys == set()
    assert tokens.picture_treatment == "none"
    assert tokens.locale == "en"


def test_typography_display_tracking_curve_present():
    from lib.dsl.tokens import Tokens

    raw = {
        "color": {"ink": "#111", "accent": "#f00", "paper": "#fff"},
        "font-family": {"display": ["Inter"], "body": ["Inter"], "mono": ["Consolas"]},
        "font-size": {"slide-title": "56px", "body": "18px", "eyebrow": "14px"},
        "font-weight": {"regular": 400, "semibold": 600, "bold": 700},
        "typography": {
            "display_tracking_curve": {"32": -0.005, "56": -0.015, "96": -0.025},
            "tnum_font": "Inter Tabular",
            "tnum_slot_keys": ["kpi_value", "axis_tick", "year"],
        },
        "picture_treatment": "desat(0.3)",
        "locale": "de",
    }
    tokens = Tokens.from_dict(raw, brand_name="test")
    assert tokens.display_tracking_curve == {32: -0.005, 56: -0.015, 96: -0.025}
    assert tokens.tnum_font == "Inter Tabular"
    assert tokens.tnum_slot_keys == {"kpi_value", "axis_tick", "year"}
    assert tokens.picture_treatment == "desat(0.3)"
    assert tokens.locale == "de"


# ---------------------------------------------------------------------------
# Layer 1 task 11.5 — chart sanitation tokens (defaults + overrides).
# ---------------------------------------------------------------------------


def test_chart_tokens_default_values():
    from lib.dsl.tokens import Tokens
    minimal = {
        "color": {"ink": "#111", "accent": "#f00", "paper": "#fff"},
        "font-family": {"display": ["Inter"], "body": ["Inter"], "mono": ["Consolas"]},
        "font-size": {"slide-title": "56px", "body": "18px", "eyebrow": "14px"},
        "font-weight": {"regular": 400, "semibold": 600, "bold": 700},
    }
    tokens = Tokens.from_dict(minimal, brand_name="test")
    assert tokens.chart_chrome == "minimal"
    assert tokens.chart_axis_color_role == "neutral-faint"
    assert tokens.chart_legend_threshold == 4


def test_chart_tokens_overridable():
    from lib.dsl.tokens import Tokens
    raw = {
        "color": {"ink": "#111", "accent": "#f00", "paper": "#fff"},
        "font-family": {"display": ["Inter"], "body": ["Inter"], "mono": ["Consolas"]},
        "font-size": {"slide-title": "56px", "body": "18px", "eyebrow": "14px"},
        "font-weight": {"regular": 400, "semibold": 600, "bold": 700},
        "chart": {
            "chrome": "full",
            "axis_color_role": "graphite",
            "legend_threshold": 2,
        },
    }
    tokens = Tokens.from_dict(raw, brand_name="test")
    assert tokens.chart_chrome == "full"
    assert tokens.chart_axis_color_role == "graphite"
    assert tokens.chart_legend_threshold == 2


def test_resolve_style_brand_override_merges_partial():
    """A brand may declare a top-level `style` map; entries are merged on
    top of the canonical STYLE_BUNDLES bundle. Unspecified keys inherit."""
    from lib.dsl.tokens import Tokens
    raw = {
        "color": {"ink": "#111", "accent": "#f00", "paper": "#fff", "graphite": "#444"},
        "font-family": {"display": ["Inter"], "body": ["Inter"], "mono": ["Consolas"]},
        "font-size": {"slide-title": "56px", "body": "18px", "eyebrow": "14px"},
        "font-weight": {"light": 300, "regular": 400, "bold": 700},
        "style": {
            # Override only weight + letter_spacing; font/size/color/transform inherit.
            "title": {"weight": "light", "letter_spacing": -0.01},
        },
    }
    tokens = Tokens.from_dict(raw, brand_name="test")
    resolved = tokens.resolve_style("title")
    assert resolved.weight == 300                # override applied
    assert resolved.letter_spacing == -0.01      # override applied
    assert resolved.size_px == 56.0              # inherited from canonical (size: slide-title)


def test_resolve_style_brand_override_clears_transform():
    """Setting `transform: null` in the brand override clears the
    canonical transform (e.g. some brands' eyebrow is mixed-case, not UPPER)."""
    from lib.dsl.tokens import Tokens
    raw = {
        "color": {"ink": "#111", "accent": "#f00", "paper": "#fff", "graphite": "#444"},
        "font-family": {"display": ["Inter"], "body": ["Inter"], "mono": ["Consolas"]},
        "font-size": {"slide-title": "56px", "body": "18px", "eyebrow": "14px"},
        "font-weight": {"regular": 400, "bold": 700},
        "style": {
            "eyebrow": {"transform": None, "font": "body", "color": "graphite"},
        },
    }
    tokens = Tokens.from_dict(raw, brand_name="test")
    resolved = tokens.resolve_style("eyebrow")
    assert resolved.transform is None            # cleared
    assert resolved.font_family == ["Inter"]     # body family from override
    assert resolved.color_hex.lower() == "#444"  # graphite via override


def test_resolve_style_brand_override_absent_is_noop():
    """Brands without a `style` map resolve to the canonical STYLE_BUNDLES."""
    from lib.dsl.tokens import Tokens
    raw = {
        "color": {"ink": "#111", "accent": "#f00", "paper": "#fff"},
        "font-family": {"display": ["Inter"], "body": ["Inter"], "mono": ["Consolas"]},
        "font-size": {"slide-title": "56px", "body": "18px", "eyebrow": "14px"},
        "font-weight": {"regular": 400, "bold": 700},
    }
    tokens = Tokens.from_dict(raw, brand_name="test")
    resolved = tokens.resolve_style("title")
    # Canonical `title` bundle is weight=bold; absence of `style` leaves it.
    assert resolved.weight == 700
