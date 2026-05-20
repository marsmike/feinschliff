"""Tests for lib.layout_discovery — mirrors test_brand_discovery.py structure."""
from pathlib import Path

import pytest

from feinschliff.layout_discovery import (
    LayoutSource,
    Layout,
    discover_layouts,
    find_layout,
    all_layout_dirs,
)


def _write_layout(root: Path, name: str) -> Path:
    """Create a minimal .slide.dsl file in *root* and return its path."""
    root.mkdir(parents=True, exist_ok=True)
    f = root / f"{name}.slide.dsl"
    f.write_text(f"# layout: {name}\n")
    return f


# ---------------------------------------------------------------------------
# Behaviour 1: bundled layouts are discovered
# ---------------------------------------------------------------------------

def test_discover_layouts_finds_bundled(tmp_path, monkeypatch):
    bundled = tmp_path / "bundled" / "layouts"
    _write_layout(bundled, "alpha")
    _write_layout(bundled, "beta")
    monkeypatch.setenv("FEINSCHLIFF_LAYOUT_PATH", "")
    monkeypatch.setattr("feinschliff.layout_discovery._bundled_layouts_root", lambda: bundled)
    monkeypatch.setattr("feinschliff.layout_discovery._user_layouts_root", lambda: tmp_path / "no-such")
    monkeypatch.setattr("feinschliff.layout_discovery._plugin_layouts_roots", lambda: [])
    monkeypatch.setattr("feinschliff.layout_discovery._cwd_dev_layouts_roots", lambda: [])

    sources = discover_layouts()
    assert len(sources) == 1
    assert sources[0].kind == "bundled"
    assert sources[0].path == bundled


def test_find_layout_finds_bundled(tmp_path, monkeypatch):
    bundled = tmp_path / "bundled" / "layouts"
    _write_layout(bundled, "title-orange")
    monkeypatch.setenv("FEINSCHLIFF_LAYOUT_PATH", "")
    monkeypatch.setattr("feinschliff.layout_discovery._bundled_layouts_root", lambda: bundled)
    monkeypatch.setattr("feinschliff.layout_discovery._user_layouts_root", lambda: tmp_path / "no-such")
    monkeypatch.setattr("feinschliff.layout_discovery._plugin_layouts_roots", lambda: [])
    monkeypatch.setattr("feinschliff.layout_discovery._cwd_dev_layouts_roots", lambda: [])

    layout = find_layout("title-orange")
    assert layout is not None
    assert layout.name == "title-orange"
    assert layout.path == bundled / "title-orange.slide.dsl"


# ---------------------------------------------------------------------------
# Behaviour 2: priority order — bundled wins over env for same name; env
# wins when bundled doesn't have the layout (tested separately below)
# ---------------------------------------------------------------------------

def test_bundled_wins_over_env(tmp_path, monkeypatch):
    """Bundled source (priority 1) is returned before env (priority 3) for the same name."""
    bundled = tmp_path / "bundled" / "layouts"
    _write_layout(bundled, "cover")

    env_dir = tmp_path / "env-layouts"
    _write_layout(env_dir, "cover")  # same name — bundled should win

    monkeypatch.setenv("FEINSCHLIFF_LAYOUT_PATH", str(env_dir))
    monkeypatch.setattr("feinschliff.layout_discovery._bundled_layouts_root", lambda: bundled)
    monkeypatch.setattr("feinschliff.layout_discovery._user_layouts_root", lambda: tmp_path / "no-such")
    monkeypatch.setattr("feinschliff.layout_discovery._plugin_layouts_roots", lambda: [])
    monkeypatch.setattr("feinschliff.layout_discovery._cwd_dev_layouts_roots", lambda: [])

    layout = find_layout("cover")
    assert layout is not None
    assert layout.path == bundled / "cover.slide.dsl"  # bundled path, not env


def test_env_wins_for_layouts_absent_from_bundled(tmp_path, monkeypatch):
    """Env source wins when the layout is absent from bundled (priority falls through)."""
    bundled = tmp_path / "bundled" / "layouts"
    bundled.mkdir(parents=True)  # exists but has no layouts

    env_dir = tmp_path / "env-layouts"
    _write_layout(env_dir, "env-only-slide")  # only in env

    monkeypatch.setenv("FEINSCHLIFF_LAYOUT_PATH", str(env_dir))
    monkeypatch.setattr("feinschliff.layout_discovery._bundled_layouts_root", lambda: bundled)
    monkeypatch.setattr("feinschliff.layout_discovery._user_layouts_root", lambda: tmp_path / "no-such")
    monkeypatch.setattr("feinschliff.layout_discovery._plugin_layouts_roots", lambda: [])
    monkeypatch.setattr("feinschliff.layout_discovery._cwd_dev_layouts_roots", lambda: [])

    layout = find_layout("env-only-slide")
    assert layout is not None
    assert layout.path == env_dir / "env-only-slide.slide.dsl"


def test_env_override_wins_no_bundled(tmp_path, monkeypatch):
    """When bundled doesn't have the layout, env is used."""
    bundled = tmp_path / "bundled" / "layouts"
    bundled.mkdir(parents=True)  # exists but has no layouts

    env_dir = tmp_path / "env-layouts"
    _write_layout(env_dir, "custom-slide")

    monkeypatch.setenv("FEINSCHLIFF_LAYOUT_PATH", str(env_dir))
    monkeypatch.setattr("feinschliff.layout_discovery._bundled_layouts_root", lambda: bundled)
    monkeypatch.setattr("feinschliff.layout_discovery._user_layouts_root", lambda: tmp_path / "no-such")
    monkeypatch.setattr("feinschliff.layout_discovery._plugin_layouts_roots", lambda: [])
    monkeypatch.setattr("feinschliff.layout_discovery._cwd_dev_layouts_roots", lambda: [])

    layout = find_layout("custom-slide")
    assert layout is not None
    assert layout.path == env_dir / "custom-slide.slide.dsl"


def test_env_path_layout_appears_in_all_layout_dirs(tmp_path, monkeypatch):
    """all_layout_dirs() returns env directories."""
    bundled = tmp_path / "bundled" / "layouts"
    bundled.mkdir(parents=True)
    env_dir = tmp_path / "env-layouts"
    env_dir.mkdir(parents=True)

    monkeypatch.setenv("FEINSCHLIFF_LAYOUT_PATH", str(env_dir))
    monkeypatch.setattr("feinschliff.layout_discovery._bundled_layouts_root", lambda: bundled)
    monkeypatch.setattr("feinschliff.layout_discovery._user_layouts_root", lambda: tmp_path / "no-such")
    monkeypatch.setattr("feinschliff.layout_discovery._plugin_layouts_roots", lambda: [])
    monkeypatch.setattr("feinschliff.layout_discovery._cwd_dev_layouts_roots", lambda: [])

    dirs = all_layout_dirs()
    assert bundled in dirs
    assert env_dir in dirs


# ---------------------------------------------------------------------------
# Behaviour 3: missing layout returns None
# ---------------------------------------------------------------------------

def test_find_layout_returns_none_when_missing(tmp_path, monkeypatch):
    bundled = tmp_path / "bundled" / "layouts"
    bundled.mkdir(parents=True)  # exists but empty

    monkeypatch.setenv("FEINSCHLIFF_LAYOUT_PATH", "")
    monkeypatch.setattr("feinschliff.layout_discovery._bundled_layouts_root", lambda: bundled)
    monkeypatch.setattr("feinschliff.layout_discovery._user_layouts_root", lambda: tmp_path / "no-such")
    monkeypatch.setattr("feinschliff.layout_discovery._plugin_layouts_roots", lambda: [])
    monkeypatch.setattr("feinschliff.layout_discovery._cwd_dev_layouts_roots", lambda: [])

    result = find_layout("nonexistent-layout")
    assert result is None


def test_find_layout_returns_none_no_sources(tmp_path, monkeypatch):
    """When no source directories exist, find_layout returns None (no crash)."""
    monkeypatch.setenv("FEINSCHLIFF_LAYOUT_PATH", "")
    monkeypatch.setattr("feinschliff.layout_discovery._bundled_layouts_root", lambda: tmp_path / "no-bundled")
    monkeypatch.setattr("feinschliff.layout_discovery._user_layouts_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr("feinschliff.layout_discovery._plugin_layouts_roots", lambda: [])
    monkeypatch.setattr("feinschliff.layout_discovery._cwd_dev_layouts_roots", lambda: [])

    result = find_layout("anything")
    assert result is None


# ---------------------------------------------------------------------------
# Additional coverage: multiple env paths, dataclass fields
# ---------------------------------------------------------------------------

def test_layout_dataclass_fields(tmp_path, monkeypatch):
    bundled = tmp_path / "bundled" / "layouts"
    _write_layout(bundled, "my-layout")

    monkeypatch.setenv("FEINSCHLIFF_LAYOUT_PATH", "")
    monkeypatch.setattr("feinschliff.layout_discovery._bundled_layouts_root", lambda: bundled)
    monkeypatch.setattr("feinschliff.layout_discovery._user_layouts_root", lambda: tmp_path / "no-such")
    monkeypatch.setattr("feinschliff.layout_discovery._plugin_layouts_roots", lambda: [])
    monkeypatch.setattr("feinschliff.layout_discovery._cwd_dev_layouts_roots", lambda: [])

    layout = find_layout("my-layout")
    assert isinstance(layout, Layout)
    assert layout.name == "my-layout"
    assert layout.path.name == "my-layout.slide.dsl"


def test_layout_source_dataclass_fields(tmp_path, monkeypatch):
    bundled = tmp_path / "bundled" / "layouts"
    bundled.mkdir(parents=True)

    monkeypatch.setenv("FEINSCHLIFF_LAYOUT_PATH", "")
    monkeypatch.setattr("feinschliff.layout_discovery._bundled_layouts_root", lambda: bundled)
    monkeypatch.setattr("feinschliff.layout_discovery._user_layouts_root", lambda: tmp_path / "no-such")
    monkeypatch.setattr("feinschliff.layout_discovery._plugin_layouts_roots", lambda: [])
    monkeypatch.setattr("feinschliff.layout_discovery._cwd_dev_layouts_roots", lambda: [])

    sources = discover_layouts()
    assert len(sources) == 1
    src = sources[0]
    assert isinstance(src, LayoutSource)
    assert src.kind == "bundled"
    assert src.path == bundled


def test_multiple_env_paths(tmp_path, monkeypatch):
    """Colon-separated FEINSCHLIFF_LAYOUT_PATH yields multiple sources."""
    bundled = tmp_path / "bundled" / "layouts"
    bundled.mkdir(parents=True)
    env_a = tmp_path / "env-a"
    env_a.mkdir(parents=True)
    env_b = tmp_path / "env-b"
    env_b.mkdir(parents=True)

    monkeypatch.setenv("FEINSCHLIFF_LAYOUT_PATH", f"{env_a}:{env_b}")
    monkeypatch.setattr("feinschliff.layout_discovery._bundled_layouts_root", lambda: bundled)
    monkeypatch.setattr("feinschliff.layout_discovery._user_layouts_root", lambda: tmp_path / "no-such")
    monkeypatch.setattr("feinschliff.layout_discovery._plugin_layouts_roots", lambda: [])
    monkeypatch.setattr("feinschliff.layout_discovery._cwd_dev_layouts_roots", lambda: [])

    dirs = all_layout_dirs()
    assert env_a in dirs
    assert env_b in dirs


def test_real_bundled_layouts_are_discoverable():
    """Smoke test: the actual bundled layouts/ directory is discoverable."""
    layouts = discover_layouts()
    assert len(layouts) >= 1
    bundled = [s for s in layouts if s.kind == "bundled"]
    assert bundled, "bundled layouts source must always be present"
    assert bundled[0].path.is_dir()


def test_find_layout_finds_real_title_orange():
    """Smoke test: title-orange is a real layout that must be findable."""
    layout = find_layout("title-orange")
    assert layout is not None
    assert layout.path.is_file()
    assert layout.path.name == "title-orange.slide.dsl"
