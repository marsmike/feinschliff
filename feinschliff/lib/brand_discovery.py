"""Locate brand packs across bundled, plugin-installed, env, and user-local paths."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Brand:
    name: str
    root: Path
    tokens_path: Path | None = None
    design_path: Path | None = None
    layouts_path: Path | None = None   # brand-specific layouts/ (overrides toolkit)
    compounds_path: Path | None = None # brand-specific compounds/


def _bundled_brands_root() -> Path:
    """The brands/ directory shipped inside this plugin."""
    return Path(__file__).resolve().parents[1] / "brands"


def _user_brands_root() -> Path:
    return Path.home() / ".feinschliff" / "brands"


def _plugin_brands_roots() -> list[Path]:
    """`brands/` dirs from installed Claude Code plugins.

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
                brands = plugin / "brands"
                if brands.is_dir():
                    roots.append(brands)
    for entry in sorted(plugins.iterdir()):
        if entry.name == "marketplaces" or not entry.is_dir():
            continue
        brands = entry / "brands"
        if brands.is_dir():
            roots.append(brands)
    return roots


def _env_brands_roots() -> list[Path]:
    raw = os.environ.get("FEINSCHLIFF_BRAND_PATH", "")
    return [Path(p) for p in raw.split(os.pathsep) if p]


def _cwd_dev_brands_roots() -> list[Path]:
    """Walk up from $CWD; if an in-place git checkout of feinschliff exists,
    surface its brands/. Supports the dev workflow where a brand author edits
    `~/work/feinschliff/feinschliff/brands/<brand>/` and runs scripts that
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
        candidate = ancestor / "feinschliff" / "brands"
        if candidate.is_dir():
            out.append(candidate)
        # Also handle a checkout where the cwd is already inside `feinschliff/`.
        sibling = ancestor / "brands"
        if (ancestor / "pyproject.toml").is_file() and sibling.is_dir():
            out.append(sibling)
        if (ancestor / ".git").exists():
            break
    return out


def _discovery_sources() -> list[tuple[str, Path]]:
    """Source-tagged list used by both discovery and the not-found error."""
    items: list[tuple[str, Path]] = [("bundled", _bundled_brands_root())]
    items.extend(("plugin", p) for p in _plugin_brands_roots())
    items.extend(("env", p) for p in _env_brands_roots())
    items.extend(("cwd-dev", p) for p in _cwd_dev_brands_roots())
    items.append(("user", _user_brands_root()))
    return items


def discover_brands() -> list[Brand]:
    """Returns all brands found across all discovery sources, deduped by name (first wins).

    A brand is a directory containing either `tokens.json` (the v2 marker)
    or `DESIGN.md` (with token frontmatter). Brands inherit toolkit-level
    layouts and may add brand-specific ones via `layouts/`.

    Sources scanned, in priority order:
      1. bundled — `brands/` next to the installed `lib/`
      2. plugin — `~/.claude/plugins/.../brands/`
      3. env — directories listed in `FEINSCHLIFF_BRAND_PATH` (colon-separated)
      4. cwd-dev — `feinschliff/brands/` reachable by walking up from $CWD
      5. user — `~/.feinschliff/brands/`
    """
    seen: dict[str, Brand] = {}
    for _src, root in _discovery_sources():
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            if not d.is_dir():
                continue
            tokens = d / "tokens.json"
            design = d / "DESIGN.md"
            if not (tokens.is_file() or design.is_file()):
                continue
            if d.name in seen:
                continue
            seen[d.name] = Brand(
                name=d.name, root=d,
                tokens_path=tokens if tokens.is_file() else None,
                design_path=design if design.is_file() else None,
                layouts_path=(d / "layouts") if (d / "layouts").is_dir() else None,
                compounds_path=(d / "compounds") if (d / "compounds").is_dir() else None,
            )
    return list(seen.values())


def find_brand(name: str) -> Brand:
    """Return the brand with the given name, or raise ValueError with a
    diagnostic listing every searched path and every brand actually found.

    This is the function `/deck --brand <name>` should call — its error
    message tells the user exactly what to fix.
    """
    brands = discover_brands()
    for b in brands:
        if b.name == name:
            return b
    available = sorted(b.name for b in brands)
    searched_lines = []
    for src, root in _discovery_sources():
        marker = "✓" if root.is_dir() else "·"
        searched_lines.append(f"  {marker} [{src}] {root}")
    searched = "\n".join(searched_lines)
    raise ValueError(
        f"brand '{name}' not found.\n"
        f"available brands: {', '.join(available) or '(none)'}\n"
        f"searched paths:\n{searched}\n"
        f"to add a brand path, set FEINSCHLIFF_BRAND_PATH=/abs/path[:/another]"
    )
