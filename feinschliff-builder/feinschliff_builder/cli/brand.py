"""`feinschliff brand …` subcommand router (v2)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from feinschliff.brand_discovery import discover_brands
import feinschliff as _feinschliff_pkg


# Toolkit-shared layouts/compounds (inherited by every brand).
# These live in the core feinschliff plugin, not in the builder plugin.
_TOOLKIT_ROOT = Path(_feinschliff_pkg.__file__).resolve().parent.parent
_TOOLKIT_LAYOUTS = _TOOLKIT_ROOT / "layouts"
_TOOLKIT_COMPOUNDS = _TOOLKIT_ROOT / "compounds"


def register(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest="brand_command", required=True)

    p_list = sub.add_parser("list", help="List discovered brand packs")
    p_list.set_defaults(func=cmd_list)

    p_inspect = sub.add_parser("inspect", help="Print v2 inventory for a brand")
    p_inspect.add_argument("name")
    p_inspect.set_defaults(func=cmd_inspect)


def cmd_list(_args) -> int:
    for b in discover_brands():
        markers = []
        if b.tokens_path:
            markers.append("tokens")
        if b.design_path:
            markers.append("design")
        if b.layouts_path:
            markers.append("+layouts")
        if b.compounds_path:
            markers.append("+compounds")
        tag = ",".join(markers) or "?"
        print(f"{b.name}\t{tag}\t{b.root}")
    return 0


def _toolkit_layouts() -> list[str]:
    if not _TOOLKIT_LAYOUTS.is_dir():
        return []
    return sorted(p.stem.replace(".slide", "") for p in _TOOLKIT_LAYOUTS.glob("*.slide.dsl"))


def _brand_layouts(brand) -> list[str]:
    if not brand.layouts_path:
        return []
    return sorted(p.stem.replace(".slide", "") for p in brand.layouts_path.glob("*.slide.dsl"))


def _brand_compounds(brand) -> list[str]:
    if not brand.compounds_path:
        return []
    return sorted(p.stem for p in brand.compounds_path.glob("*.dsl"))


def _inheritance_chain(brand) -> list[str]:
    """Walk the `extends:` chain from DESIGN.md frontmatter starting at
    `brand`. Returns names parent-most → child (e.g. ["feinschliff",
    "feinschliff-dark"]). Missing DESIGN.md or missing parents truncate
    the walk silently — the caller decides how to render. Cycles raise
    ValueError."""
    try:
        from feinschliff.design_md import parse as parse_design_md
    except Exception:
        return [brand.name]

    brands_by_name = {b.name: b for b in discover_brands()}
    chain: list[str] = []
    visited: set[str] = set()
    cur = brand
    while True:
        if cur.name in visited:
            raise ValueError(f"cyclic brand inheritance through {cur.name}")
        visited.add(cur.name)
        chain.append(cur.name)
        if not cur.design_path or not cur.design_path.is_file():
            break
        try:
            dm = parse_design_md(cur.design_path)
        except Exception:
            break
        parent_name = getattr(dm, "extends", None)
        if not parent_name:
            break
        parent = brands_by_name.get(parent_name)
        if parent is None:
            chain.append(parent_name)  # show the missing parent for diagnostics
            break
        cur = parent
    return list(reversed(chain))


def cmd_inspect(args) -> int:
    brand = next((b for b in discover_brands() if b.name == args.name), None)
    if brand is None:
        print(f"brand not found: {args.name}", file=sys.stderr)
        return 1

    print(f"brand: {brand.name}")
    print(f"root:  {brand.root}")

    # Inheritance chain (parent-most → child). Silent on missing DESIGN.md.
    try:
        chain = _inheritance_chain(brand)
    except ValueError as e:
        print(f"inheritance: ERROR — {e}", file=sys.stderr)
        chain = [brand.name]
    if len(chain) > 1:
        print(f"inheritance: {' → '.join(chain)}")

    # Tokens summary.
    if brand.tokens_path:
        try:
            tokens = json.loads(brand.tokens_path.read_text())
            colors = tokens.get("color", {})
            fonts  = tokens.get("font-family", {})
            sizes  = tokens.get("font-size", {})
            print(f"tokens.json: {len(colors)} colors, {len(fonts)} font families, {len(sizes)} sizes")
            asset_sources = tokens.get("asset_sources")
            if asset_sources:
                kinds = [k for k in asset_sources if not k.startswith("$")]
                if kinds:
                    print(f"asset_sources: {', '.join(kinds)}")
        except (OSError, json.JSONDecodeError) as e:
            print(f"tokens.json: unreadable ({e})", file=sys.stderr)
    elif brand.design_path:
        print("DESIGN.md frontmatter only — no separate tokens.json")
    else:
        print("(no tokens.json or DESIGN.md)")

    # Layout inventory.
    inherited = _toolkit_layouts()
    overrides = _brand_layouts(brand)
    inherited_active = [n for n in inherited if n not in overrides]
    brand_only = [n for n in overrides if n not in inherited]
    overridden = [n for n in overrides if n in inherited]
    print(f"layouts: {len(inherited_active) + len(overrides)} "
          f"({len(inherited_active)} inherited, {len(overridden)} overridden, "
          f"{len(brand_only)} brand-only)")
    if overridden:
        print(f"  overrides: {', '.join(overridden)}")
    if brand_only:
        print(f"  brand-only: {', '.join(brand_only)}")

    # Brand compounds.
    bc = _brand_compounds(brand)
    if bc:
        print(f"compounds: {len(bc)} ({', '.join(bc)})")

    return 0
