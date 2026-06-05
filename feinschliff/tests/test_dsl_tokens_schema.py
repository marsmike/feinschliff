"""Schema-validation tests for `lib.dsl.tokens.load_tokens` / `validate_tokens`.

Guards the JSON schema at `lib/schemas/tokens.schema.json` against drift —
both that real brand packs still validate and that obviously bad shapes
get rejected with a useful message.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from feinschliff.dsl.tokens import load_tokens, validate_tokens


REPO_ROOT = Path(__file__).resolve().parents[1]
BRANDS_DIR = REPO_ROOT / "brands"
_EXTRA_BRANDS_DIR = REPO_ROOT.parent / "feinschliff-extra" / "brands"


def test_valid_feinschliff_brand_passes_schema():
    """The shipped feinschliff brand pack must validate cleanly."""
    # If validation fails this raises; the assert is belt-and-braces.
    tokens = load_tokens(BRANDS_DIR / "feinschliff", brands_dir=BRANDS_DIR)
    assert tokens.brand_name == "feinschliff"
    # And the raw json passes the standalone validator with no issues.
    raw = json.loads((BRANDS_DIR / "feinschliff" / "tokens.json").read_text())
    validate_tokens(raw, "feinschliff")  # must not raise


def test_valid_inherited_brand_passes_schema(tmp_path):
    """A brand that extends another (catppuccin-macchiato → feinschliff) validates after merge."""
    _macchiato_brands = (
        _EXTRA_BRANDS_DIR
        if _EXTRA_BRANDS_DIR.exists() and (_EXTRA_BRANDS_DIR / "catppuccin-macchiato").exists()
        else BRANDS_DIR
    )
    macchiato_dir = _macchiato_brands / "catppuccin-macchiato"
    if not macchiato_dir.exists():
        pytest.skip("catppuccin-macchiato not available (install feinschliff-extra)")
    # When macchiato lives in the extra brands dir, feinschliff (the parent)
    # won't be found there. Build a combined brands_dir with symlinks so
    # load_tokens can walk the full extends chain.
    if not (_macchiato_brands / "feinschliff").exists():
        combined = tmp_path / "brands"
        combined.mkdir()
        import shutil
        try:
            (combined / "feinschliff").symlink_to(BRANDS_DIR / "feinschliff")
        except OSError:
            shutil.copytree(BRANDS_DIR / "feinschliff", combined / "feinschliff")
        try:
            (combined / "catppuccin-macchiato").symlink_to(macchiato_dir)
        except OSError:
            shutil.copytree(macchiato_dir, combined / "catppuccin-macchiato")
        brands_search = combined
        macchiato_dir = combined / "catppuccin-macchiato"
    else:
        brands_search = _macchiato_brands
    tokens = load_tokens(macchiato_dir, brands_dir=brands_search)
    assert tokens.brand_name == "catppuccin-macchiato"


def test_missing_required_group_raises_with_useful_message():
    """A tokens dict missing `font-family` should fail with a clear, named error."""
    bad = {
        "color": {"accent": "#FF0000"},
        # 'font-family' deliberately omitted
        "font-size": {"body": "26px"},
    }
    with pytest.raises(ValueError) as exc:
        validate_tokens(bad, "fake-brand")
    msg = str(exc.value)
    assert "fake-brand" in msg
    assert "tokens.json validation failed" in msg
    assert "font-family" in msg


def test_invalid_color_shape_raises():
    """A non-dict, non-string color value should be rejected."""
    bad = {
        "color": {"accent": 12345},   # neither hex string nor DTCG object
        "font-family": {"display": ["Noto Sans"]},
        "font-size": {"body": "26px"},
    }
    with pytest.raises(ValueError) as exc:
        validate_tokens(bad, "bad-color-brand")
    assert "bad-color-brand" in str(exc.value)
    assert "color.accent" in str(exc.value)


def test_invalid_font_size_unit_raises():
    """Font sizes must end with px — bare numbers or other units are rejected."""
    bad = {
        "color": {"accent": "#FF0000"},
        "font-family": {"display": ["Noto Sans"]},
        "font-size": {"body": "26"},   # missing px suffix
    }
    with pytest.raises(ValueError) as exc:
        validate_tokens(bad, "bad-size-brand")
    assert "font-size.body" in str(exc.value)


def test_image_provider_valid_minimal():
    """`$image_provider` with only `kind` is valid (config is optional)."""
    ok = {
        "color": {"accent": "#FF0000"},
        "font-family": {"display": ["Noto Sans"]},
        "font-size": {"body": "26px"},
        "$image_provider": {"kind": "unsplash"},
    }
    validate_tokens(ok, "ok-brand")  # must not raise


def test_image_provider_valid_with_config():
    """`$image_provider` with a free-form `config` object is valid."""
    ok = {
        "color": {"accent": "#FF0000"},
        "font-family": {"display": ["Noto Sans"]},
        "font-size": {"body": "26px"},
        "$image_provider": {
            "kind": "unsplash",
            "config": {"access_key": "abc123", "per_page": 5},
        },
    }
    validate_tokens(ok, "ok-cfg-brand")  # must not raise


def test_image_provider_missing_kind_raises():
    """`$image_provider` without required `kind` is rejected."""
    bad = {
        "color": {"accent": "#FF0000"},
        "font-family": {"display": ["Noto Sans"]},
        "font-size": {"body": "26px"},
        "$image_provider": {},
    }
    with pytest.raises(ValueError) as exc:
        validate_tokens(bad, "no-kind-brand")
    msg = str(exc.value)
    assert "no-kind-brand" in msg
    assert "$image_provider" in msg
    assert "kind" in msg


def test_image_provider_extra_field_raises():
    """`$image_provider` rejects unknown fields (additionalProperties:false)."""
    bad = {
        "color": {"accent": "#FF0000"},
        "font-family": {"display": ["Noto Sans"]},
        "font-size": {"body": "26px"},
        "$image_provider": {"kind": "unsplash", "rogue": 1},
    }
    with pytest.raises(ValueError) as exc:
        validate_tokens(bad, "rogue-field-brand")
    msg = str(exc.value)
    assert "rogue-field-brand" in msg
    assert "$image_provider" in msg


def test_image_provider_config_must_be_object():
    """`$image_provider.config` must be an object, not a string."""
    bad = {
        "color": {"accent": "#FF0000"},
        "font-family": {"display": ["Noto Sans"]},
        "font-size": {"body": "26px"},
        "$image_provider": {"kind": "unsplash", "config": "string-not-object"},
    }
    with pytest.raises(ValueError) as exc:
        validate_tokens(bad, "bad-cfg-brand")
    msg = str(exc.value)
    assert "bad-cfg-brand" in msg
    assert "config" in msg


def test_load_tokens_surfaces_schema_error_for_bad_brand(tmp_path):
    """A brand pack with a malformed tokens.json should surface validation error from load_tokens."""
    brand = tmp_path / "shabby"
    brand.mkdir()
    (brand / "tokens.json").write_text(json.dumps({
        # Missing every required group.
        "$description": "broken on purpose",
    }))
    with pytest.raises(ValueError) as exc:
        load_tokens(brand, brands_dir=tmp_path)
    msg = str(exc.value)
    assert "shabby" in msg
    assert "tokens.json validation failed" in msg
