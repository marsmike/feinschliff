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

import pytest

from feinschmiede.brand_discovery import discover_brands
from feinschmiede.dsl.tokens import load_tokens


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
    monkeypatch.setattr("feinschmiede.brand_discovery._bundled_brands_root", lambda: bundled)
    monkeypatch.setattr("feinschmiede.brand_discovery._user_brands_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr("feinschmiede.brand_discovery._plugin_brands_roots", lambda: [])
    monkeypatch.setattr("feinschmiede.brand_discovery._cwd_dev_brands_roots", lambda: [])

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
    monkeypatch.setattr("feinschmiede.brand_discovery._bundled_brands_root", lambda: bundled)
    monkeypatch.setattr("feinschmiede.brand_discovery._user_brands_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr("feinschmiede.brand_discovery._plugin_brands_roots", lambda: [])
    monkeypatch.setattr("feinschmiede.brand_discovery._cwd_dev_brands_roots", lambda: [])

    [b] = [x for x in discover_brands() if x.name == "with-provider"]
    assert b.image_provider_config == {
        "kind": "unsplash",
        "config": {"rate_limit": 50},
    }


# ---------------------------------------------------------------------------
# discover_brands → Brand.image_provider_config is extends-resolved
# ---------------------------------------------------------------------------


def test_brand_image_provider_resolved_via_discover_brands(tmp_path, monkeypatch):
    """A child brand without its own `$image_provider` must surface the
    parent's via `discover_brands` → `Brand.image_provider_config` (the
    field is spec'd as extends-resolved, not the raw child-only block).

    Also covers the override case: when the child swaps `kind`, the
    Brand surfaces the child's `kind` and the parent's `config` is
    dropped (kind-swap invalidates parent config — same semantic as
    `load_tokens`).
    """
    bundled = tmp_path / "bundled" / "brands"
    bundled.mkdir(parents=True, exist_ok=True)
    # Parent declares the provider; child inherits, no override.
    _write_brand(
        bundled,
        "parent",
        tokens_extra={
            "$image_provider": {
                "kind": "unsplash",
                "config": {"api_version": "v1", "rate_limit": 50},
            }
        },
    )
    _write_brand(bundled, "child", extends="parent")
    # A second child that swaps `kind` — parent's config must NOT carry.
    _write_brand(
        bundled,
        "child-swapped",
        extends="parent",
        tokens_extra={"$image_provider": {"kind": "vendor-designkit"}},
    )

    monkeypatch.setenv("FEINSCHLIFF_BRAND_PATH", "")
    monkeypatch.setattr("feinschmiede.brand_discovery._bundled_brands_root", lambda: bundled)
    monkeypatch.setattr("feinschmiede.brand_discovery._user_brands_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr("feinschmiede.brand_discovery._plugin_brands_roots", lambda: [])
    monkeypatch.setattr("feinschmiede.brand_discovery._cwd_dev_brands_roots", lambda: [])

    brands = {b.name: b for b in discover_brands()}

    # Inheritance: child surfaces the parent's full provider block.
    assert brands["child"].image_provider_config == {
        "kind": "unsplash",
        "config": {"api_version": "v1", "rate_limit": 50},
    }

    # Override (kind swap): child wins; parent's config is dropped.
    swapped = brands["child-swapped"].image_provider_config
    assert swapped is not None
    assert swapped["kind"] == "vendor-designkit"
    assert swapped.get("config") in (None, {})


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
            "$image_provider": {"kind": "vendor-designkit"},
        },
    )

    tokens = load_tokens(tmp_path / "child", brands_dir=tmp_path)
    assert tokens.raw["$image_provider"]["kind"] == "vendor-designkit"
    # Parent's config does NOT carry over — kind swap invalidates it.
    assert "config" not in tokens.raw["$image_provider"] or \
        tokens.raw["$image_provider"].get("config") in (None, {})


@pytest.mark.xfail(
    reason=(
        "tokens.schema.json now constrains $image_provider to {kind, config} "
        "with additionalProperties:false (Task 5). A hypothetical future "
        "extension key like `enabled` no longer passes validation, so this "
        "future-shape invariant cannot be exercised through load_tokens "
        "until the schema grows. The precise-drop merge logic in "
        "lib/dsl/tokens.py (drop only `config`, not the whole parent block) "
        "is preserved as future-proofing. When a new top-level "
        "$image_provider key lands in the schema, re-enable this test "
        "and audit the kind-swap block per its contract comment."
    ),
    strict=True,
)
def test_kind_swap_preserves_non_config_parent_keys(tmp_path):
    """When the child swaps `kind`, the parent's `config` is dropped (scoped
    to a different provider) but any OTHER parent-level `$image_provider`
    keys survive.

    Today `$image_provider` only carries `kind` + `config` (enforced by
    tokens.schema.json as of Task 5), so this test primarily locks in the
    invariant for future shape extensions (e.g. `enabled`, `fallback`).
    The schema's additionalProperties:false on $image_provider means the
    test key below currently fails validation — see the @pytest.mark.xfail.
    """
    _write_brand(
        tmp_path,
        "parent",
        tokens_extra={
            "$image_provider": {
                "kind": "unsplash",
                "config": {"api_version": "v1"},
                # Future-shape key — not in the schema today, but the merge
                # engine must preserve it across kind-swaps. If validation
                # ever tightens to reject this key, this test will FAIL
                # AT VALIDATION and signal the audit-this-block contract
                # comment in lib/dsl/tokens.py needs honoring.
                "enabled": False,
            }
        },
    )
    _write_brand(
        tmp_path,
        "child",
        extends="parent",
        tokens_extra={"$image_provider": {"kind": "vendor-designkit"}},
    )

    tokens = load_tokens(tmp_path / "child", brands_dir=tmp_path)
    ip = tokens.raw["$image_provider"]
    # Kind from child wins.
    assert ip["kind"] == "vendor-designkit"
    # Parent's `config` was dropped (provider-scoped, not portable).
    assert "config" not in ip or ip.get("config") in (None, {})
    # Parent's non-`config` key SURVIVES — the precise-drop, not whole-block-clear.
    assert ip.get("enabled") is False


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
