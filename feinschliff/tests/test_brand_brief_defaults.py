"""Tests for brand-pack-level brief priors (D1).

Covers:
- Schema validates tokens.json WITH brief_defaults present.
- Schema validates tokens.json WITHOUT brief_defaults (back-compat).
- Schema REJECTS tokens.json with brief_defaults.verbosity = "bogus".
- load_brief_defaults returns the dict for a brand that has brief_defaults.
- load_brief_defaults returns {} for a brand without.
- All existing brand tokens.json files still validate (regression).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

FEINSCHLIFF_ROOT = Path(__file__).resolve().parents[1]
BRANDS_DIR = FEINSCHLIFF_ROOT / "brands"
_EXTRA_BRANDS_DIR = FEINSCHLIFF_ROOT.parent / "feinschliff-extra" / "brands"

sys.path.insert(0, str(FEINSCHLIFF_ROOT))


def _find_brand(name: str) -> Path | None:
    """Return the brand directory, checking core then extra brands. Returns None if not found."""
    core = BRANDS_DIR / name
    if core.exists():
        return core
    extra = _EXTRA_BRANDS_DIR / name
    if extra.exists():
        return extra
    return None

from feinschmiede.dsl.tokens import load_brief_defaults, validate_tokens


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_VALID = {
    "color": {"accent": "#4C566A"},
    "font-family": {"display": ["Inter"]},
    "font-size": {"body": "26px"},
}


def _with_brief_defaults(**kw) -> dict:
    """Return a minimal valid tokens dict with brief_defaults added."""
    d = dict(MINIMAL_VALID)
    d["brief_defaults"] = kw
    return d


# ---------------------------------------------------------------------------
# Schema: brief_defaults present and valid
# ---------------------------------------------------------------------------


def test_schema_accepts_tokens_with_full_brief_defaults():
    """A tokens.json with all four brief_defaults keys should pass validation."""
    tokens = _with_brief_defaults(
        verbosity="concise",
        image_style="minimal",
        frame="scqa",
        audience="exec",
    )
    validate_tokens(tokens, "test-brand")  # must not raise


def test_schema_accepts_tokens_with_partial_brief_defaults():
    """All sub-keys are optional — a partial brief_defaults block is valid."""
    tokens = _with_brief_defaults(verbosity="standard")
    validate_tokens(tokens, "test-brand-partial")


def test_schema_accepts_tokens_with_empty_brief_defaults():
    """An empty brief_defaults object {} is allowed (all sub-keys optional)."""
    tokens = _with_brief_defaults()
    validate_tokens(tokens, "test-brand-empty-defaults")


# ---------------------------------------------------------------------------
# Schema: back-compat — tokens.json WITHOUT brief_defaults is still valid
# ---------------------------------------------------------------------------


def test_schema_accepts_tokens_without_brief_defaults():
    """brief_defaults is optional — tokens without it must still validate."""
    validate_tokens(MINIMAL_VALID, "test-brand-no-defaults")


# ---------------------------------------------------------------------------
# Schema: enum constraint enforcement
# ---------------------------------------------------------------------------


def test_schema_rejects_invalid_verbosity():
    """brief_defaults.verbosity='bogus' must be rejected (enum constraint)."""
    tokens = _with_brief_defaults(verbosity="bogus")
    with pytest.raises(ValueError) as exc:
        validate_tokens(tokens, "bad-verbosity-brand")
    assert "verbosity" in str(exc.value)


def test_schema_rejects_invalid_image_style():
    """brief_defaults.image_style='holographic' must be rejected."""
    tokens = _with_brief_defaults(image_style="holographic")
    with pytest.raises(ValueError) as exc:
        validate_tokens(tokens, "bad-image-style-brand")
    assert "image_style" in str(exc.value)


def test_schema_rejects_invalid_frame():
    """brief_defaults.frame='hero-journey' must be rejected (enum constraint)."""
    tokens = _with_brief_defaults(frame="hero-journey")
    with pytest.raises(ValueError) as exc:
        validate_tokens(tokens, "bad-frame-brand")
    assert "frame" in str(exc.value)


def test_schema_accepts_man_in_hole_frame():
    """The canonical frame name is 'man-in-hole' (no '-a-'). It must be accepted."""
    tokens = _with_brief_defaults(frame="man-in-hole")
    validate_tokens(tokens, "man-in-hole-brand")  # must not raise


def test_schema_rejects_man_in_a_hole_frame():
    """'man-in-a-hole' (with '-a-') is the wrong spelling and must be rejected."""
    tokens = _with_brief_defaults(frame="man-in-a-hole")
    with pytest.raises(ValueError) as exc:
        validate_tokens(tokens, "man-in-a-hole-brand")
    assert "frame" in str(exc.value)


def test_schema_rejects_invalid_audience():
    """brief_defaults.audience='board' must be rejected (enum constraint)."""
    tokens = _with_brief_defaults(audience="board")
    with pytest.raises(ValueError) as exc:
        validate_tokens(tokens, "bad-audience-brand")
    assert "audience" in str(exc.value)


def test_schema_rejects_unknown_key_in_brief_defaults():
    """additionalProperties:false — unknown keys must be rejected."""
    tokens = _with_brief_defaults(verbosity="concise", tone="casual")
    with pytest.raises(ValueError) as exc:
        validate_tokens(tokens, "extra-key-brand")
    assert "tone" in str(exc.value) or "brief_defaults" in str(exc.value)


# ---------------------------------------------------------------------------
# load_brief_defaults — returns dict for brand that has it
# ---------------------------------------------------------------------------


def test_load_brief_defaults_returns_dict_for_nord(tmp_path):
    """load_brief_defaults returns the brief_defaults block for a brand that has one."""
    brand = tmp_path / "nord"
    brand.mkdir()
    tokens = dict(MINIMAL_VALID)
    tokens["brief_defaults"] = {"verbosity": "concise", "image_style": "minimal", "frame": "scqa"}
    (brand / "tokens.json").write_text(json.dumps(tokens))
    result = load_brief_defaults(brand)
    assert result == {"verbosity": "concise", "image_style": "minimal", "frame": "scqa"}


def test_load_brief_defaults_returns_empty_for_brand_without(tmp_path):
    """load_brief_defaults returns {} for a brand that has no brief_defaults block."""
    brand = tmp_path / "no-defaults"
    brand.mkdir()
    (brand / "tokens.json").write_text(json.dumps(MINIMAL_VALID))
    result = load_brief_defaults(brand)
    assert result == {}


def test_load_brief_defaults_returns_empty_when_no_tokens_json(tmp_path):
    """load_brief_defaults returns {} gracefully when tokens.json doesn't exist."""
    brand = tmp_path / "ghost-brand"
    brand.mkdir()
    result = load_brief_defaults(brand)
    assert result == {}


def test_load_brief_defaults_warns_on_unknown_keys(tmp_path, capsys):
    """load_brief_defaults emits a stderr warning for unknown keys but doesn't raise."""
    brand = tmp_path / "weird-brand"
    brand.mkdir()
    tokens = dict(MINIMAL_VALID)
    tokens["brief_defaults"] = {"verbosity": "concise", "tone": "formal"}
    (brand / "tokens.json").write_text(json.dumps(tokens))
    result = load_brief_defaults(brand)
    # Unknown key should be returned (passthrough) but warned about.
    assert "verbosity" in result
    captured = capsys.readouterr()
    assert "tone" in captured.err


# ---------------------------------------------------------------------------
# Regression: all existing brands still validate with updated schema
# ---------------------------------------------------------------------------


# Brands known to have pre-existing schema issues unrelated to D1.
# gs-ramspau is missing the required `font-size` group — pre-existing defect,
# tracked separately. Do not fix here; just mark xfail so D1 regression tests
# still surface any NEW breakage in all other brands.
_PRE_EXISTING_SCHEMA_FAILURES: set[str] = {"gs-ramspau"}


@pytest.mark.parametrize(
    "brand_dir",
    sorted(BRANDS_DIR.iterdir()),
    ids=lambda p: p.name,
)
def test_existing_brand_still_validates(brand_dir):
    """All shipped brands must still validate after the schema update (additive change)."""
    tokens_file = brand_dir / "tokens.json"
    if not tokens_file.is_file():
        pytest.skip(f"No tokens.json in {brand_dir.name}")
    if brand_dir.name in _PRE_EXISTING_SCHEMA_FAILURES:
        pytest.xfail(
            f"Brand '{brand_dir.name}' has a pre-existing schema failure "
            f"(missing required group) — unrelated to D1."
        )
    raw = json.loads(tokens_file.read_text())
    validate_tokens(raw, brand_dir.name)  # must not raise


# ---------------------------------------------------------------------------
# Real nord brand uses load_brief_defaults
# ---------------------------------------------------------------------------


def test_nord_brand_load_brief_defaults():
    """If the nord brand has brief_defaults in tokens.json, load_brief_defaults returns it."""
    nord_dir = _find_brand("nord")
    if nord_dir is None:
        pytest.skip("nord brand not available (install feinschliff-extra)")
    result = load_brief_defaults(nord_dir)
    # Nord should have brief_defaults after D1.
    assert isinstance(result, dict)
    assert result.get("verbosity") == "concise"
    assert result.get("image_style") == "minimal"
