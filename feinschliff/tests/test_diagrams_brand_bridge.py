"""Tests for lib/diagrams/brand_bridge.py — semantic color resolution."""
from __future__ import annotations

from pathlib import Path

import pytest

from feinschliff.diagrams.brand_bridge import (
    SEMANTIC_NAMES,
    BrandBridgeError,
    resolve,
    resolve_with_pack,
)
from feinschliff.brand import BrandPack


def _brand_dir(name: str) -> Path:
    core = Path(__file__).resolve().parent.parent / "brands" / name
    if core.exists():
        return core
    extra = Path(__file__).resolve().parent.parent.parent / "feinschliff-extra" / "brands" / name
    return extra  # may not exist; caller handles FileNotFoundError


def test_vocabulary_is_frozen_at_planned_size():
    """The vocabulary is fixed at 25 names — extending it is a coordinated change
    across brand_bridge, brand packs, and DSL references.

    25 = 19 base + 6 `chart-series-N` (N=1..6) for pie/doughnut slice
    colours (added in PR #19). The 19 base was: original 17 +
    `off-white` (always-light fg, paired with chapter-slab) +
    `chapter-slab` (always-dark bg for `theme dark` and chapter
    dividers, decoupled from `ink` which inverts between light/dark
    brands).
    """
    assert len(SEMANTIC_NAMES) == 25
    # Spot-check representative members from each group
    assert "primary" in SEMANTIC_NAMES       # brand
    assert "paper" in SEMANTIC_NAMES          # surface
    assert "off-white" in SEMANTIC_NAMES      # surface (always-light fg)
    assert "chapter-slab" in SEMANTIC_NAMES   # surface (always-dark bg)
    assert "success" in SEMANTIC_NAMES        # severity
    assert "status-on" in SEMANTIC_NAMES      # status
    assert "chart-series-1" in SEMANTIC_NAMES # chart-slice ramp head
    assert "chart-series-6" in SEMANTIC_NAMES # chart-slice ramp tail


def test_unknown_name_rejected():
    with pytest.raises(BrandBridgeError, match="unknown color token 'royal-blue'"):
        resolve("royal-blue", _brand_dir("feinschliff"))


def test_literal_hex_passes_through():
    # Hex literals are accepted unchanged so the hybrid decompiler's
    # source-fidelity fallback (raw `#RRGGBB` for colours that have no
    # close brand-token match) survives the SVG-render path. Other
    # literal forms — rgb()/hsl() — are still rejected.
    assert resolve("#4f46e5", _brand_dir("feinschliff")) == "#4f46e5"
    assert resolve("#abc", _brand_dir("feinschliff")) == "#abc"


def test_rgb_rejected():
    with pytest.raises(BrandBridgeError, match="literal color"):
        resolve("rgb(79,70,229)", _brand_dir("feinschliff"))


def test_primary_resolves_to_brand_indigo_for_feinschliff():
    hex_color = resolve("primary", _brand_dir("feinschliff"))
    assert hex_color.startswith("#")
    assert len(hex_color) == 7  # #RRGGBB


def test_extends_inheritance_resolves_from_parent():
    """A brand that inherits via extends: pulls tokens from its parent."""
    # feinschliff-dark extends feinschliff (verified in feinschliff-dark/DESIGN.md).
    bd = _brand_dir("feinschliff-dark")
    if not bd.exists():
        import pytest
        pytest.skip("feinschliff-dark not available (install feinschliff-extra)")
    primary = resolve("primary", bd)
    assert primary.startswith("#"), f"got {primary!r}"


def test_dollar_value_token_shape(tmp_path):
    """Tokens stored as {'$value': '#xxx'} are unwrapped correctly."""
    brand = tmp_path / "myco"
    brand.mkdir()
    (brand / "tokens.json").write_text('{"color": {"accent": {"$value": "#abcdef"}}}')
    (brand / "DESIGN.md").write_text("---\nname: MyCo\n---\n")
    result = resolve("primary", brand)
    assert result == "#abcdef"


def test_missing_token_slot_raises(tmp_path):
    """A brand whose tokens.json lacks a required slot raises BrandBridgeError."""
    brand = tmp_path / "myco"
    brand.mkdir()
    (brand / "tokens.json").write_text('{"color": {}}')
    (brand / "DESIGN.md").write_text("---\nname: MyCo\n---\n")
    with pytest.raises(BrandBridgeError, match="missing token"):
        resolve("primary", brand)


@pytest.mark.parametrize("brand_name", [
    "blank",
    "feinschliff", "feinschliff-dark",
    "catppuccin-latte", "catppuccin-macchiato",
    "solarized-dark", "nord", "gruvbox-dark",
    "gs-ramspau",
    "claude", "binance", "ferrari", "spotify",
])
def test_all_semantic_names_resolve_for_every_brand(brand_name):
    """Every shipped brand pack must resolve every semantic name to a valid hex.

    17 semantic names × 12 brands = 204 happy cases enforced.
    """
    brand_dir = _brand_dir(brand_name)
    if not brand_dir.exists():
        pytest.skip(f"brand {brand_name} not present in this checkout")
    for name in SEMANTIC_NAMES:
        hex_color = resolve(name, brand_dir)
        assert hex_color.startswith("#"), (
            f"brand {brand_name} / name {name}: got {hex_color!r}"
        )
        assert len(hex_color) in (4, 7, 9), (
            f"brand {brand_name} / name {name}: malformed hex {hex_color!r}"
        )


from feinschliff.diagrams.brand_bridge import resolve_brand_dir


def test_brand_resolution_directive_wins(monkeypatch):
    monkeypatch.setenv("FEINSCHLIFF_BRAND", "nord")
    out = resolve_brand_dir(
        directive="catppuccin-macchiato",
        cli_flag="gruvbox-dark",
        deck_context="feinschliff",
    )
    assert out.name == "catppuccin-macchiato"


def test_brand_resolution_cli_wins_over_env(monkeypatch):
    monkeypatch.setenv("FEINSCHLIFF_BRAND", "nord")
    out = resolve_brand_dir(
        directive=None,
        cli_flag="gruvbox-dark",
        deck_context="feinschliff",
    )
    assert out.name == "gruvbox-dark"


def test_brand_resolution_env_wins_over_deck(monkeypatch):
    monkeypatch.setenv("FEINSCHLIFF_BRAND", "nord")
    out = resolve_brand_dir(
        directive=None,
        cli_flag=None,
        deck_context="feinschliff",
    )
    assert out.name == "nord"


def test_brand_resolution_default_to_feinschliff(monkeypatch):
    monkeypatch.delenv("FEINSCHLIFF_BRAND", raising=False)
    out = resolve_brand_dir(
        directive=None,
        cli_flag=None,
        deck_context=None,
    )
    assert out.name == "feinschliff"


# ---------------------------------------------------------------------------
# resolve_with_pack — typed BrandPack entry point
# ---------------------------------------------------------------------------

def test_resolve_with_pack_returns_same_as_resolve():
    """resolve_with_pack delegates to resolve and returns the same hex."""
    pack = BrandPack.load(_brand_dir("feinschliff"))
    via_pack = resolve_with_pack("primary", pack)
    via_path = resolve("primary", _brand_dir("feinschliff"))
    assert via_pack == via_path


def test_resolve_with_pack_raises_on_unknown_name():
    pack = BrandPack.load(_brand_dir("feinschliff"))
    with pytest.raises(BrandBridgeError):
        resolve_with_pack("totally-unknown-token-xyz", pack)
