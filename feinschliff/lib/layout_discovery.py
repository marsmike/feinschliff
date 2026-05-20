"""Locate toolkit layout packs across bundled, plugin-installed, env, and user-local paths."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Layout:
    name: str          # stem of the .slide.dsl file, e.g. "title-orange"
    path: Path         # absolute path to the .slide.dsl file


@dataclass
class LayoutSource:
    kind: str          # "bundled" | "plugin" | "env" | "cwd-dev" | "user"
    path: Path         # the layouts/ directory


def _bundled_layouts_root() -> Path:
    """The layouts/ directory shipped inside this plugin."""
    return Path(__file__).resolve().parents[1] / "layouts"


def _user_layouts_root() -> Path:
    return Path.home() / ".feinschliff" / "layouts"


def _plugin_layouts_roots() -> list[Path]:
    """`layouts/` dirs from installed Claude Code plugins whose parent
    contains "feinschliff" in the name.

    Modern plugins land under ``~/.claude/plugins/marketplaces/{marketplace}/{plugin}/``;
    sideloaded plugins occasionally land directly under ``~/.claude/plugins/{plugin}/``.
    Both layouts are supported.
    """
    plugins = Path.home() / ".claude" / "plugins"
    if not plugins.is_dir():
        return []
    roots: list[Path] = []
    marketplaces = plugins / "marketplaces"
    if marketplaces.is_dir():
        for marketplace in sorted(marketplaces.iterdir()):
            if not marketplace.is_dir():
                continue
            for plugin in sorted(marketplace.iterdir()):
                if "feinschliff" not in plugin.name and "feinschliff" not in marketplace.name:
                    continue
                layouts = plugin / "layouts"
                if layouts.is_dir():
                    roots.append(layouts)
    for entry in sorted(plugins.iterdir()):
        if entry.name == "marketplaces" or not entry.is_dir():
            continue
        if "feinschliff" not in entry.name:
            continue
        layouts = entry / "layouts"
        if layouts.is_dir():
            roots.append(layouts)
    return roots


def _env_layouts_roots() -> list[Path]:
    raw = os.environ.get("FEINSCHLIFF_LAYOUT_PATH", "")
    return [Path(p) for p in raw.split(os.pathsep) if p]


def _cwd_dev_layouts_roots() -> list[Path]:
    """Walk up from $CWD; if an in-place git checkout of feinschliff exists,
    surface its layouts/. Supports the dev workflow where a layout author edits
    `~/work/feinschliff/feinschliff/layouts/<layout>/` and runs scripts that
    don't sit inside the package.

    The walk stops at the first git boundary so we don't accidentally scan
    the whole home directory.
    """
    out: list[Path] = []
    try:
        cwd = Path.cwd().resolve()
    except FileNotFoundError:
        return out
    for ancestor in [cwd, *cwd.parents]:
        candidate = ancestor / "feinschliff" / "layouts"
        if candidate.is_dir():
            out.append(candidate)
        # Also handle a checkout where the cwd is already inside `feinschliff/`.
        sibling = ancestor / "layouts"
        if (ancestor / "pyproject.toml").is_file() and sibling.is_dir():
            out.append(sibling)
        if (ancestor / ".git").exists():
            break
    return out


def _discovery_sources() -> list[tuple[str, Path]]:
    """Source-tagged list used by both discovery and the not-found error."""
    items: list[tuple[str, Path]] = [("bundled", _bundled_layouts_root())]
    items.extend(("plugin", p) for p in _plugin_layouts_roots())
    items.extend(("env", p) for p in _env_layouts_roots())
    items.extend(("cwd-dev", p) for p in _cwd_dev_layouts_roots())
    items.append(("user", _user_layouts_root()))
    return items


def discover_layouts() -> list[LayoutSource]:
    """Returns all layout source directories found across all discovery sources, deduped by path.

    Sources scanned, in priority order:
      1. bundled — `layouts/` next to the installed `lib/`
      2. plugin — `~/.claude/plugins/.../layouts/` (feinschliff plugins only)
      3. env — directories listed in `FEINSCHLIFF_LAYOUT_PATH` (colon-separated)
      4. cwd-dev — `feinschliff/layouts/` reachable by walking up from $CWD
      5. user — `~/.feinschliff/layouts/`
    """
    seen_paths: set[Path] = set()
    sources: list[LayoutSource] = []
    for src, root in _discovery_sources():
        if not root.is_dir():
            continue
        resolved = root.resolve()
        if resolved in seen_paths:
            continue
        seen_paths.add(resolved)
        sources.append(LayoutSource(kind=src, path=root))
    return sources


def all_layout_dirs() -> list[Path]:
    """Return all existing layout directories in priority order."""
    return [src.path for src in discover_layouts()]


def find_layout(name: str) -> Layout | None:
    """Return the layout with the given name (without .slide.dsl suffix), or None.

    Searches all discovery sources in priority order. The first match wins.
    """
    filename = f"{name}.slide.dsl"
    for src in discover_layouts():
        candidate = src.path / filename
        if candidate.is_file():
            return Layout(name=name, path=candidate)
    return None
