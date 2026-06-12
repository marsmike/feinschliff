"""Brand-tinted picture placeholders (2026-06-12 gallery spec §3.2a).

Brands may declare explicit duotone endpoints in tokens
(``picture_duotone: {dark: ink, light: accent}``); the placeholder path
auto-duotones to brand identity when no treatment is configured; and a
brand can override the shared gem illustration by shipping
``assets/illustrations/placeholder.jpg`` in its own pack.
"""
from __future__ import annotations


from feinschliff.dsl.pptx_emit import (
    EmitContext,
    _duotone_endpoints_for_brand,
    _placeholder_image_path,
    _placeholder_treatment,
)


class _FakeTokens:
    def __init__(self, colors, raw=None, treatment="none"):
        self._colors = colors
        self.raw = raw or {}
        self.picture_treatment = treatment

    def color(self, name):
        return self._colors[name]


_BRAND = {"ink": "#000000", "paper": "#FFFFFF", "accent": "#D85A20"}


def test_explicit_picture_duotone_wins_over_heuristic():
    """ink/paper gap is 255 (>80) — the heuristic would return grayscale;
    the explicit declaration forces ink→accent."""
    tokens = _FakeTokens(_BRAND, raw={"picture_duotone": {"dark": "ink", "light": "accent"}})
    assert _duotone_endpoints_for_brand(tokens) == ((0, 0, 0), (216, 90, 32))


def test_heuristic_unchanged_without_declaration():
    tokens = _FakeTokens(_BRAND)
    assert _duotone_endpoints_for_brand(tokens) == ((0, 0, 0), (255, 255, 255))


def test_invalid_declaration_falls_back_to_heuristic():
    tokens = _FakeTokens(_BRAND, raw={"picture_duotone": {"dark": "nope", "light": "accent"}})
    assert _duotone_endpoints_for_brand(tokens) == ((0, 0, 0), (255, 255, 255))


def test_placeholder_auto_duotones_when_no_treatment_configured():
    """treatment 'none' → the placeholder still tints to brand endpoints."""
    tokens = _FakeTokens(_BRAND, raw={"picture_duotone": {"dark": "ink", "light": "accent"}})
    treatment, dark, light = _placeholder_treatment(tokens)
    assert treatment == "duotone"
    assert (dark, light) == ((0, 0, 0), (216, 90, 32))


def test_placeholder_respects_explicit_treatment():
    tokens = _FakeTokens(_BRAND, treatment="desat")
    treatment, dark, light = _placeholder_treatment(tokens)
    assert treatment == "desat"
    assert dark is None and light is None


def test_brand_asset_root_overrides_shared_placeholder(tmp_path):
    brand_assets = tmp_path / "brand-assets"
    (brand_assets / "illustrations").mkdir(parents=True)
    override = brand_assets / "illustrations" / "placeholder.jpg"
    override.write_bytes(b"not-really-a-jpeg")
    fallback_assets = tmp_path / "plugin-assets"
    (fallback_assets / "illustrations").mkdir(parents=True)
    (fallback_assets / "illustrations" / "placeholder.jpg").write_bytes(b"x")

    ctx = EmitContext(tokens=_FakeTokens(_BRAND), asset_root=brand_assets,
                      asset_root_fallback=fallback_assets)
    assert _placeholder_image_path(ctx) == override

    ctx2 = EmitContext(tokens=_FakeTokens(_BRAND), asset_root=None,
                       asset_root_fallback=fallback_assets)
    assert _placeholder_image_path(ctx2) == (
        fallback_assets / "illustrations" / "placeholder.jpg")


def test_explicit_declaration_beats_inherited_treatment():
    """Packs extending a parent inherit its picture_treatment (e.g.
    desat(0.3) from the toolkit brand). An explicit picture_duotone
    declaration is the stronger signal for placeholders."""
    tokens = _FakeTokens(_BRAND, treatment="desat(0.3)",
                         raw={"picture_duotone": {"dark": "ink", "light": "accent"}})
    treatment, dark, light = _placeholder_treatment(tokens)
    assert treatment == "duotone"
    assert (dark, light) == ((0, 0, 0), (216, 90, 32))
