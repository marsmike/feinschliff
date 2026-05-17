import json
from pathlib import Path

import pytest

from lib.brand_discovery import discover_brands, find_brand, Brand


def _write_brand(root: Path, name: str) -> Path:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    # tokens.json is the v2 brand marker. (V1's catalog.json detection was
    # removed in 2026-05-16 — no shipped brand ever used catalog.json under
    # the v2 pipeline.)
    (d / "tokens.json").write_text(json.dumps({"name": name, "colors": {}}))
    return d


def test_discover_brands_finds_bundled(tmp_path, monkeypatch):
    bundled = tmp_path / "bundled" / "brands"
    _write_brand(bundled, "alpha")
    _write_brand(bundled, "beta")
    monkeypatch.setenv("FEINSCHLIFF_BRAND_PATH", "")
    monkeypatch.setattr("lib.brand_discovery._bundled_brands_root", lambda: bundled)
    monkeypatch.setattr("lib.brand_discovery._user_brands_root", lambda: tmp_path / "no-such")
    monkeypatch.setattr("lib.brand_discovery._plugin_brands_roots", lambda: [])
    monkeypatch.setattr("lib.brand_discovery._cwd_dev_brands_roots", lambda: [])

    brands = discover_brands()
    names = sorted(b.name for b in brands)
    assert names == ["alpha", "beta"]


def test_discover_brands_finds_env_path(tmp_path, monkeypatch):
    extra = tmp_path / "extra"
    _write_brand(extra, "gamma")
    monkeypatch.setenv("FEINSCHLIFF_BRAND_PATH", str(extra))
    monkeypatch.setattr("lib.brand_discovery._bundled_brands_root", lambda: tmp_path / "no-bundled")
    monkeypatch.setattr("lib.brand_discovery._user_brands_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr("lib.brand_discovery._plugin_brands_roots", lambda: [])
    monkeypatch.setattr("lib.brand_discovery._cwd_dev_brands_roots", lambda: [])

    brands = discover_brands()
    assert any(b.name == "gamma" for b in brands)


def test_brand_dataclass_carries_paths(tmp_path, monkeypatch):
    bundled = tmp_path / "bundled" / "brands"
    d = _write_brand(bundled, "delta")
    monkeypatch.setenv("FEINSCHLIFF_BRAND_PATH", "")
    monkeypatch.setattr("lib.brand_discovery._bundled_brands_root", lambda: bundled)
    monkeypatch.setattr("lib.brand_discovery._user_brands_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr("lib.brand_discovery._plugin_brands_roots", lambda: [])
    monkeypatch.setattr("lib.brand_discovery._cwd_dev_brands_roots", lambda: [])

    [delta] = [b for b in discover_brands() if b.name == "delta"]
    assert delta.root == d
    assert delta.tokens_path == d / "tokens.json"


def test_plugin_brands_roots_walks_marketplace_layout(tmp_path, monkeypatch):
    """Marketplace-installed plugins live under ~/.claude/plugins/marketplaces/{m}/{plugin}/brands."""
    fake_home = tmp_path / "home"
    plugins = fake_home / ".claude" / "plugins"
    team = plugins / "marketplaces" / "acme-team" / "feinschliff-acme" / "brands"
    team.mkdir(parents=True)
    oss = plugins / "marketplaces" / "feinschliff" / "feinschliff" / "brands"
    oss.mkdir(parents=True)

    monkeypatch.setenv("HOME", str(fake_home))

    from lib.brand_discovery import _plugin_brands_roots
    roots = _plugin_brands_roots()
    assert team in roots
    assert oss in roots


def test_plugin_brands_roots_includes_sideload_layout(tmp_path, monkeypatch):
    """Sideloaded plugins live directly under ~/.claude/plugins/{plugin}/brands."""
    fake_home = tmp_path / "home"
    plugins = fake_home / ".claude" / "plugins"
    sideload = plugins / "legacy-plugin" / "brands"
    sideload.mkdir(parents=True)

    monkeypatch.setenv("HOME", str(fake_home))

    from lib.brand_discovery import _plugin_brands_roots
    roots = _plugin_brands_roots()
    assert sideload in roots


def test_cwd_dev_brands_roots_finds_in_place_checkout(tmp_path, monkeypatch):
    """When $CWD is inside a feinschliff/ git checkout, brands/ should be discovered."""
    checkout = tmp_path / "agentic-toolkit"
    (checkout / ".git").mkdir(parents=True)
    fb = checkout / "feinschliff"
    (fb / "brands").mkdir(parents=True)
    _write_brand(fb / "brands", "in-place-brand")
    # Run from somewhere inside the checkout.
    monkeypatch.chdir(fb / "brands" / "in-place-brand")

    from lib.brand_discovery import _cwd_dev_brands_roots
    roots = _cwd_dev_brands_roots()
    assert (fb / "brands") in roots


def test_find_brand_raises_with_diagnostic(tmp_path, monkeypatch):
    bundled = tmp_path / "bundled" / "brands"
    _write_brand(bundled, "alpha")
    monkeypatch.setenv("FEINSCHLIFF_BRAND_PATH", "")
    monkeypatch.setattr("lib.brand_discovery._bundled_brands_root", lambda: bundled)
    monkeypatch.setattr("lib.brand_discovery._user_brands_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr("lib.brand_discovery._plugin_brands_roots", lambda: [])
    monkeypatch.setattr("lib.brand_discovery._cwd_dev_brands_roots", lambda: [])

    found = find_brand("alpha")
    assert found.name == "alpha"

    with pytest.raises(ValueError) as exc:
        find_brand("does-not-exist")
    msg = str(exc.value)
    assert "does-not-exist" in msg
    assert "alpha" in msg          # lists available
    assert "[bundled]" in msg      # tags the searched source
    assert "FEINSCHLIFF_BRAND_PATH" in msg


def test_discover_brands_ignores_dir_without_brand_marker(tmp_path, monkeypatch):
    """A directory without `tokens.json` or `DESIGN.md` is not a brand."""
    bundled = tmp_path / "bundled" / "brands"
    empty_brand = bundled / "no-marker"
    empty_brand.mkdir(parents=True)

    monkeypatch.setenv("FEINSCHLIFF_BRAND_PATH", "")
    monkeypatch.setattr("lib.brand_discovery._bundled_brands_root", lambda: bundled)
    monkeypatch.setattr("lib.brand_discovery._user_brands_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr("lib.brand_discovery._plugin_brands_roots", lambda: [])
    monkeypatch.setattr("lib.brand_discovery._cwd_dev_brands_roots", lambda: [])

    assert "no-marker" not in {b.name for b in discover_brands()}
