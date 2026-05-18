"""Tests for `$image_provider` propagation through brand discovery + tokens loader.

The `$image_provider` block lives at the top of `tokens.json`. It is read
by `lib.brand_discovery.discover_brands()` onto `Brand.image_provider_config`
and walks `extends` chains in `lib.dsl.tokens.load_tokens` with these
semantics:

  - `kind` is full-replaced when the child provides it.
  - `config` is deep-merged when the child does not override `kind`.
  - If the child swaps `kind`, parent's `config` is dropped (scoped to a
    different provider; not portable).

These tests pin the four explicit plan cases plus a deep-merge regression
guard.
"""
from __future__ import annotations

import json
from pathlib import Path

from lib.brand_discovery import discover_brands
from lib.dsl.tokens import load_tokens


# Minimal tokens.json scaffold required by the loader's schema. Tests that
# exercise `load_tokens` end-to-end against the merged schema need this;
# tests that only check `discover_brands` field population can use a
# leaner stub since discovery does not validate.
_VALID_TOKENS_BASE: dict[str, object] = {
    "color": {"ink": "#111111", "accent": "#ff0000", "paper": "#ffffff"},
    "font-family": {
        "display": ["Inter"],
        "body": ["Inter"],
        "mono": ["Consolas"],
    },
    "font-size": {"slide-title": "56px", "body": "18px", "eyebrow": "14px"},
    "font-weight": {"regular": 400, "semibold": 600, "bold": 700},
}


def _write_brand(
    root: Path,
    name: str,
    *,
    tokens_extra: dict | None = None,
    extends: str | None = None,
) -> Path:
    """Stage a brand pack under `root/name/`. Returns the brand dir."""
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    body: dict = dict(_VALID_TOKENS_BASE)
    if tokens_extra:
        body.update(tokens_extra)
    (d / "tokens.json").write_text(json.dumps(body))
    if extends:
        (d / "DESIGN.md").write_text(f"---\nextends: {extends}\n---\n")
    return d


# ---------------------------------------------------------------------------
# discover_brands → Brand.image_provider_config
# ---------------------------------------------------------------------------


def test_brand_without_image_provider_has_none(tmp_path, monkeypatch):
    """A brand pack with no `$image_provider` → field is None."""
    bundled = tmp_path / "bundled" / "brands"
    _write_brand(bundled, "plain")
    monkeypatch.setenv("FEINSCHLIFF_BRAND_PATH", "")
    monkeypatch.setattr("lib.brand_discovery._bundled_brands_root", lambda: bundled)
    monkeypatch.setattr("lib.brand_discovery._user_brands_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr("lib.brand_discovery._plugin_brands_roots", lambda: [])
    monkeypatch.setattr("lib.brand_discovery._cwd_dev_brands_roots", lambda: [])

    [b] = [x for x in discover_brands() if x.name == "plain"]
    assert b.image_provider_config is None


def test_brand_with_image_provider_populates_field(tmp_path, monkeypatch):
    """`$image_provider` in tokens.json → Brand carries the dict verbatim."""
    bundled = tmp_path / "bundled" / "brands"
    _write_brand(
        bundled,
        "with-provider",
        tokens_extra={
            "$image_provider": {
                "kind": "unsplash",
                "config": {"rate_limit": 50},
            }
        },
    )
    monkeypatch.setenv("FEINSCHLIFF_BRAND_PATH", "")
    monkeypatch.setattr("lib.brand_discovery._bundled_brands_root", lambda: bundled)
    monkeypatch.setattr("lib.brand_discovery._user_brands_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr("lib.brand_discovery._plugin_brands_roots", lambda: [])
    monkeypatch.setattr("lib.brand_discovery._cwd_dev_brands_roots", lambda: [])

    [b] = [x for x in discover_brands() if x.name == "with-provider"]
    assert b.image_provider_config == {
        "kind": "unsplash",
        "config": {"rate_limit": 50},
    }


# ---------------------------------------------------------------------------
# load_tokens → extends chain propagates $image_provider
# ---------------------------------------------------------------------------


def test_brand_inherits_image_provider_from_parent(tmp_path):
    """Parent declares `$image_provider`; child omits → child inherits."""
    _write_brand(
        tmp_path,
        "parent",
        tokens_extra={
            "$image_provider": {
                "kind": "unsplash",
                "config": {"api_version": "v1", "rate_limit": 50},
            }
        },
    )
    _write_brand(tmp_path, "child", extends="parent")

    tokens = load_tokens(tmp_path / "child", brands_dir=tmp_path)
    assert tokens.raw["$image_provider"] == {
        "kind": "unsplash",
        "config": {"api_version": "v1", "rate_limit": 50},
    }


def test_brand_overrides_image_provider_kind(tmp_path):
    """Child overrides `kind` → child wins; parent's `config` is dropped
    because it was scoped to the parent's provider, not portable across kinds."""
    _write_brand(
        tmp_path,
        "parent",
        tokens_extra={
            "$image_provider": {
                "kind": "unsplash",
                "config": {"api_version": "v1"},
            }
        },
    )
    _write_brand(
        tmp_path,
        "child",
        extends="parent",
        tokens_extra={
            "$image_provider": {"kind": "bsh-designkit"},
        },
    )

    tokens = load_tokens(tmp_path / "child", brands_dir=tmp_path)
    assert tokens.raw["$image_provider"]["kind"] == "bsh-designkit"
    # Parent's config does NOT carry over — kind swap invalidates it.
    assert "config" not in tokens.raw["$image_provider"] or \
        tokens.raw["$image_provider"].get("config") in (None, {})


def test_brand_deep_merges_image_provider_config(tmp_path):
    """Child provides only `config` (no `kind`) → inherit parent's `kind`,
    deep-merge `config` with child winning per key.

    Locks in the deep-merge semantic so future refactors of `load_tokens`
    do not silently regress to a shallow replace.
    """
    _write_brand(
        tmp_path,
        "parent",
        tokens_extra={
            "$image_provider": {
                "kind": "unsplash",
                "config": {"api_version": "v1", "rate_limit": 50},
            }
        },
    )
    _write_brand(
        tmp_path,
        "child",
        extends="parent",
        tokens_extra={
            "$image_provider": {"config": {"rate_limit": 100}},
        },
    )

    tokens = load_tokens(tmp_path / "child", brands_dir=tmp_path)
    assert tokens.raw["$image_provider"] == {
        "kind": "unsplash",
        "config": {"api_version": "v1", "rate_limit": 100},
    }
