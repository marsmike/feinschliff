"""Brand theme — templates are brand-parameterized, never hardcoded.

Reads a brand pack's tokens.json (Design Tokens format: color.<name>.$value,
font-family.<name>.$value) and maps onto the engine's theme contract. Any
missing token falls back to the neutral default.
"""
from __future__ import annotations

import json
from pathlib import Path

from feinschnitt.edit import EditError

DEFAULT_THEME = {
    "bg": "#10131A",          # dark canvas under takeovers / letterboxing
    "surface": "#1E2430",     # card surfaces
    "text": "#F4F4F2",        # primary on-dark text
    "muted": "#A7B0BE",       # secondary text
    "accent": "#C9A24A",      # ONE accent — monogamous per frame
    "fontTitle": "Archivo",
    "fontBody": "Inter",
}

_COLOR_MAP = {           # theme key -> ordered candidate token names
    "bg": ("black", "ink", "chapter-slab"),
    "surface": ("graphite", "steel"),
    "text": ("off-white", "paper", "silver"),
    "muted": ("off-white-2", "silver", "steel"),
    "accent": ("accent", "highlight"),
}


def _token(tree: dict, group: str, name: str) -> str | list | None:
    group_tree = tree.get(group)
    if not isinstance(group_tree, dict):
        return None
    value = group_tree.get(name)
    return value.get("$value") if isinstance(value, dict) else None


def resolve_theme(brand_dir: Path | None) -> dict:
    theme = dict(DEFAULT_THEME)
    if brand_dir is None:
        return theme
    tokens_path = Path(brand_dir) / "tokens.json"
    if not tokens_path.exists():
        raise EditError(f"brand pack has no tokens.json: {tokens_path}")
    try:
        tree = json.loads(tokens_path.read_text())
    except json.JSONDecodeError as exc:
        raise EditError(f"brand tokens.json invalid: {tokens_path} ({exc})") from exc
    for key, candidates in _COLOR_MAP.items():
        for name in candidates:
            hexval = _token(tree, "color", name)
            if hexval:
                theme[key] = hexval
                break
    for theme_key, token_name in (("fontTitle", "display"), ("fontBody", "body")):
        fam = _token(tree, "font-family", token_name)
        if isinstance(fam, list):
            fam = ", ".join(str(f) for f in fam)
        if fam:
            theme[theme_key] = fam
    return theme
