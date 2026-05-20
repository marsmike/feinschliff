"""Snap every hex color in an SVG to the nearest brand-token hex.

Defensive utility for any SVG-import path (vision extraction, externally
authored diagrams, claude-design HTML compile) that may carry raw hex
values. The current refurbish pipeline emits token names by construction,
so this is not wired in by default — import and call it when a path
introduces raw hex.

Reads tokens.json from the brand pack, collects every `$value` that is a
6-digit hex, builds a palette, and rewrites every `fill="#..."` /
`stroke="#..."` / `stop-color="#..."` in the SVG to the nearest palette
hex by squared RGB distance. Returns a report mapping
{original_hex -> chosen_token_hex, replaced: bool}.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

HEX_RE = re.compile(r"#[0-9a-fA-F]{6}")
ATTR_RE = re.compile(r'(fill|stroke|stop-color)\s*=\s*"(#[0-9a-fA-F]{6})"')


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def _palette(brand_dir: Path) -> list[str]:
    tokens = json.loads((brand_dir / "tokens.json").read_text())
    found: set[str] = set()
    def walk(o):
        if isinstance(o, dict):
            v = o.get("$value")
            if isinstance(v, str) and HEX_RE.fullmatch(v):
                found.add(v.lower())
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(tokens)
    return sorted(found)


def _nearest(hex_in: str, palette: list[str]) -> str:
    r, g, b = _hex_to_rgb(hex_in)
    def d(p: str) -> int:
        pr, pg, pb = _hex_to_rgb(p)
        return (pr - r) ** 2 + (pg - g) ** 2 + (pb - b) ** 2
    return min(palette, key=d)


def snap_svg_to_brand_palette(
    src_svg: Path,
    out_svg: Path,
    *,
    brand_dir: Path,
) -> dict[str, Any]:
    palette = _palette(brand_dir)
    if not palette:
        out_svg.write_text(src_svg.read_text())
        return {"palette_size": 0, "mappings": []}

    body = src_svg.read_text()
    mappings: list[dict[str, Any]] = []

    def repl(m: re.Match) -> str:
        attr, orig = m.group(1), m.group(2).lower()
        if orig in palette:
            mappings.append({"original": orig, "chosen": orig, "replaced": False})
            return m.group(0)
        chosen = _nearest(orig, palette)
        mappings.append({"original": orig, "chosen": chosen, "replaced": True})
        return f'{attr}="{chosen}"'

    new_body = ATTR_RE.sub(repl, body)
    out_svg.write_text(new_body)
    return {"palette_size": len(palette), "mappings": mappings}
