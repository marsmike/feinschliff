"""Validate wheels-manifest.json shape for every CLI plugin (rolling-latest format).

Each manifest must have:
- release_tag: the literal string "latest"
- wheels: dict with keys py311, py312, py313
  - each value is an HTTPS URL string pointing to the latest GitHub release
  - URL basename follows the pattern <plugin>-wheels-py<minor>.tar.gz
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# Repo root is three levels up from this file (tests/feinschliff/test_*.py).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# CLI plugins that ship a bin/ launcher — each should have a wheels-manifest.json.
_CLI_PLUGINS = [
    "feinschliff",
    "feinschliff-builder",
    "feinbild",
    "feinklang",
    "feinschnitt",
]

_EXPECTED_PY_KEYS = {"py311", "py312", "py313"}


def _load_manifest(plugin: str) -> dict:
    path = _REPO_ROOT / plugin / "wheels-manifest.json"
    assert path.exists(), f"{plugin}/wheels-manifest.json does not exist"
    with path.open() as f:
        return json.load(f)


@pytest.mark.parametrize("plugin", _CLI_PLUGINS)
def test_manifest_top_level_fields(plugin: str) -> None:
    m = _load_manifest(plugin)
    assert "release_tag" in m, f"{plugin}: missing 'release_tag'"
    assert m["release_tag"] == "latest", (
        f"{plugin}: 'release_tag' must be the literal string 'latest', got {m['release_tag']!r}"
    )
    assert "wheels" in m, f"{plugin}: missing 'wheels'"
    assert isinstance(m["wheels"], dict), f"{plugin}: 'wheels' must be a dict"


@pytest.mark.parametrize("plugin", _CLI_PLUGINS)
def test_manifest_python_keys_present(plugin: str) -> None:
    m = _load_manifest(plugin)
    missing = _EXPECTED_PY_KEYS - set(m.get("wheels", {}).keys())
    assert not missing, f"{plugin}: wheels missing keys: {sorted(missing)}"


@pytest.mark.parametrize("plugin", _CLI_PLUGINS)
@pytest.mark.parametrize("pykey", sorted(_EXPECTED_PY_KEYS))
def test_manifest_wheel_entry_is_url(plugin: str, pykey: str) -> None:
    m = _load_manifest(plugin)
    url = m["wheels"][pykey]
    assert isinstance(url, str), f"{plugin}[{pykey}]: entry must be a URL string, got {type(url)}"
    assert url.startswith("https://"), f"{plugin}[{pykey}]: url must be HTTPS, got: {url}"
    assert "github.com" in url, f"{plugin}[{pykey}]: url must point to github.com, got: {url}"
    assert url.endswith(".tar.gz"), f"{plugin}[{pykey}]: url must end with .tar.gz, got: {url}"


@pytest.mark.parametrize("plugin", _CLI_PLUGINS)
def test_manifest_url_uses_latest_tag(plugin: str) -> None:
    """URLs must reference the rolling 'latest' release, not a semver tag."""
    m = _load_manifest(plugin)
    for pykey, url in m["wheels"].items():
        assert "/releases/download/latest/" in url, (
            f"{plugin}[{pykey}]: URL must use 'latest' release tag, got: {url!r}"
        )


@pytest.mark.parametrize("plugin", _CLI_PLUGINS)
def test_manifest_url_contains_plugin_name(plugin: str) -> None:
    """Tarball filename must embed the plugin directory name so assets are distinguishable."""
    m = _load_manifest(plugin)
    for pykey, url in m["wheels"].items():
        filename = url.rsplit("/", 1)[-1]
        assert plugin in filename, (
            f"{plugin}[{pykey}]: expected plugin name in tarball filename, got: {filename!r}"
        )


@pytest.mark.parametrize("plugin", _CLI_PLUGINS)
def test_manifest_tarball_name_format(plugin: str) -> None:
    """Tarball filename must be <plugin>-wheels-py<minor>.tar.gz (no version segment)."""
    m = _load_manifest(plugin)
    for pykey, url in m["wheels"].items():
        filename = url.rsplit("/", 1)[-1]
        expected = f"{plugin}-wheels-{pykey}.tar.gz"
        assert filename == expected, (
            f"{plugin}[{pykey}]: expected filename {expected!r}, got: {filename!r}"
        )
