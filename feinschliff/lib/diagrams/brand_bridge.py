"""Resolve diagram DSL semantic color names against the active brand's tokens.

Single source of truth: only colors defined in brands/<b>/tokens.json are
allowed in diagram DSL. Literal hex / rgb / hsl are rejected; unknown
semantic names are rejected with a "did you mean" hint.

## Token path mismatch (finding)

The plan assumed nested paths like ``color.brand.primary``, ``color.surface.paper``,
etc. The actual tokens.json structure is **flat**: ``color.<name>`` (e.g.
``color.accent``, ``color.paper``). ``_TOKEN_PATHS`` maps the 17 semantic DSL
names to the real flat paths in every brand pack.
"""
from __future__ import annotations

import difflib
import json
import os
import re
from pathlib import Path
from typing import Final

from lib.jsonwalk import deep_merge as _deep_merge, walk as _json_walk

# 17 semantic names, fixed. Adding to this list is a coordinated change
# across brand_bridge, brand packs, and DSL references.
SEMANTIC_NAMES: Final[frozenset[str]] = frozenset({
    # brand
    "primary", "secondary", "tertiary", "accent",
    # surface
    "paper", "ink", "off-white", "chapter-slab", "surface", "surface-2",
    # semantic
    "success", "warning", "danger",
    # neutral
    "neutral", "neutral-soft", "neutral-strong",
    # status
    "status-on", "status-off", "status-pending",
    # chart series ramp — for pie/bar/line series where the brand defines
    # a graduated tint progression of its accent. Brands without explicit
    # chart-series-N tokens fall back to color.accent (all series same hue
    # — distinguishable only by labels). Six slots cover typical chart
    # series counts; >6 is unusual and indicates a chart-redesign signal.
    "chart-series-1", "chart-series-2", "chart-series-3",
    "chart-series-4", "chart-series-5", "chart-series-6",
})

# Maps each semantic DSL name to a dotted path inside tokens.json.
#
# All paths are flat under ``color.<name>`` — the real tokens.json structure.
# This differs from the original plan which assumed nested sub-groups like
# ``color.brand.*`` and ``color.surface.*``.  All 12 brand packs in the
# portfolio use the same flat layout (verified against feinschliff, catppuccin-
# latte, catppuccin-macchiato, gruvbox-dark, nord, feinschliff-dark).
_TOKEN_PATHS: Final[dict[str, str]] = {
    # Brand colors
    # "primary" and "accent" both route to the brand-accent slot: "primary" is
    # the canonical term in the DSL; "accent" is the alias for contexts that
    # explicitly call out an accent swatch.  Both point at color.accent.
    "primary":          "color.accent",          # primary branded hue (e.g. gold in feinschliff)
    "secondary":        "color.graphite",         # secondary text / support color
    "tertiary":         "color.steel",            # tertiary / muted label color
    "accent":           "color.highlight",        # alias for primary — hover/light variant of the brand accent
    # Surface
    # "paper" and "surface" are intentional aliases: both refer to the base
    # page/canvas background.  "surface" follows Material-style naming;
    # "paper" is the Feinschliff-native term.  Same physical token, two
    # semantic entry points for author convenience.
    "paper":            "color.paper",            # base page background (Feinschliff-native name)
    "ink":              "color.ink",              # body text on light
    "off-white":        "color.off-white",        # body text on dark (always light across brands)
    "chapter-slab":     "color.chapter-slab",     # deepest contrast band (always dark across brands)
    "surface":          "color.paper",            # alias for paper — base surface (Material-style name)
    "surface-2":        "color.paper-2",          # raised / secondary surface
    # Semantic severity
    "success":          "color.severity-low",     # green / positive
    "warning":          "color.severity-medium",  # amber / caution
    "danger":           "color.severity-high",    # red-rust / critical
    # Neutral ramp
    # "neutral" and "neutral-strong" alias into the steel/graphite tones:
    # "neutral" → color.steel (mid-grey, ~500-equivalent);
    # "neutral-strong" → color.graphite (dark-grey, ~700-equivalent).
    # These map the same physical tokens as "tertiary" and "secondary"
    # but signal context (neutral ramp) rather than typographic role.
    "neutral":          "color.steel",            # alias for tertiary — mid neutral (500-equivalent)
    "neutral-soft":     "color.silver",           # light neutral (300-equivalent)
    "neutral-strong":   "color.graphite",         # alias for secondary — dark neutral (700-equivalent)
    # Status
    "status-on":        "color.status-done",      # completed / active
    "status-off":       "color.status-next",      # not started / inactive
    "status-pending":   "color.status-current",   # in-progress / pending
    # Chart-series ramp — see SEMANTIC_NAMES comment. Brand-specific
    # tokens (color.chart-series-N) define the tint progression; resolve()
    # falls back to color.accent when a slot is missing.
    "chart-series-1":   "color.chart-series-1",
    "chart-series-2":   "color.chart-series-2",
    "chart-series-3":   "color.chart-series-3",
    "chart-series-4":   "color.chart-series-4",
    "chart-series-5":   "color.chart-series-5",
    "chart-series-6":   "color.chart-series-6",
}

_LITERAL_RE: Final = re.compile(r"^(#[0-9a-fA-F]{3,8}|rgba?\(|hsla?\()")


class BrandBridgeError(ValueError):
    """Raised when a diagram DSL color cannot be resolved."""


def resolve(name: str, brand_dir: Path) -> str:
    """Resolve a semantic color name to a hex string using brand tokens.

    Raises BrandBridgeError on:
    - literal hex/rgb/hsl
    - unknown semantic name
    - brand tokens missing the slot (after extends: walk)
    """
    if _LITERAL_RE.match(name):
        # Hex literals pass through as-is. The decompile pipeline emits
        # `#RRGGBB` fills when nearest_token can't find a brand token
        # close enough to the source colour; rejecting them here would
        # leave the decompiled DSL unbuildable. Other literal forms
        # (rgb()/hsl()) are still flagged because they don't survive the
        # downstream SVG-attribute path.
        if name.startswith("#") and len(name) in (4, 7, 9):
            return name
        raise BrandBridgeError(
            f"literal color '{name}' — use semantic name "
            f"(see references/dsl-reference.md)"
        )

    if name not in SEMANTIC_NAMES:
        suggestion = _suggest(name)
        hint = f" (did you mean '{suggestion}'?)" if suggestion else ""
        raise BrandBridgeError(
            f"unknown color token '{name}'{hint} — valid: "
            f"{', '.join(sorted(SEMANTIC_NAMES))}"
        )

    tokens = _load_tokens_with_extends(brand_dir)
    path = _TOKEN_PATHS[name]
    raw = _json_walk(tokens, path)
    value = _extract_value(raw)
    # Chart-series ramp falls back to accent when the brand doesn't define
    # an explicit tint progression — all series render in the brand's
    # primary hue, distinguishable only by labels. This keeps charts
    # building on brands without per-series colors.
    if value is None and name.startswith("chart-series-"):
        raw = _json_walk(tokens, "color.accent")
        value = _extract_value(raw)
    if value is None:
        raise BrandBridgeError(
            f"brand '{brand_dir.name}' missing token '{path}' for "
            f"semantic name '{name}'"
        )
    return value


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_tokens_with_extends(brand_dir: Path, _seen: frozenset[Path] | None = None) -> dict:
    """Load tokens.json, walking extends: chain via DESIGN.md frontmatter."""
    _seen = (_seen or frozenset()) | {brand_dir.resolve()}
    tokens_path = brand_dir / "tokens.json"
    if not tokens_path.exists():
        raise BrandBridgeError(f"brand '{brand_dir.name}': tokens.json missing")
    tokens = json.loads(tokens_path.read_text())

    parent = _read_extends(brand_dir)
    if parent:
        # Try the brand's own parent dir first (in-tree brands' default).
        # Then fall back to FEINSCHLIFF_BRAND_PATH entries (out-of-tree
        # packs whose parent lives elsewhere — e.g. an external pack that
        # extends the toolkit's bundled `feinschliff` default).
        candidates: list[Path] = [brand_dir.parent / parent]
        env = os.environ.get("FEINSCHLIFF_BRAND_PATH", "")
        for root in env.split(os.pathsep):
            if root:
                candidates.append(Path(root) / parent)
        # Fall back to brand_discovery so all registered sources are searched
        # (bundled, plugin, env, cwd-dev, user) — avoids a hardcoded path.
        from lib.brand_discovery import find_brand as _find_brand
        try:
            discovered = _find_brand(parent)
            candidates.append(discovered.root)
        except ValueError:
            pass
        parent_dir = next((p for p in candidates if (p / "tokens.json").exists()), None)
        if parent_dir is None:
            raise BrandBridgeError(
                f"brand '{brand_dir.name}' extends '{parent}' but no "
                f"tokens.json found in any of: {[str(p) for p in candidates]}"
            )
        if parent_dir.resolve() in _seen:
            raise BrandBridgeError(
                f"brand '{brand_dir.name}': circular extends chain detected"
            )
        parent_tokens = _load_tokens_with_extends(parent_dir, _seen)
        tokens = _deep_merge(parent_tokens, tokens)
    return tokens


def _read_extends(brand_dir: Path) -> str | None:
    """Read extends: from brand's DESIGN.md frontmatter, if present."""
    design_md = brand_dir / "DESIGN.md"
    if not design_md.exists():
        return None
    text = design_md.read_text()
    if not text.startswith("---"):
        return None
    end = text.find("---", 3)
    if end < 0:
        return None
    frontmatter = text[3:end]
    for line in frontmatter.splitlines():
        if line.strip().startswith("extends:"):
            return line.split(":", 1)[1].strip()
    return None


def _extract_value(raw: object) -> str | None:
    """Extract a hex string from a raw token value.

    Handles both the Design Tokens draft-2 ``{"$value": "#RRGGBB"}`` shape
    and bare string values.
    """
    if isinstance(raw, dict) and "$value" in raw:
        v = raw["$value"]
        return v if isinstance(v, str) else None
    return raw if isinstance(raw, str) else None


def _suggest(unknown: str) -> str | None:
    """Return the closest semantic name by edit distance, or None."""
    matches = difflib.get_close_matches(unknown.lower(), SEMANTIC_NAMES, n=1, cutoff=0.6)
    return matches[0] if matches else None


def relative_luminance(hex_color: str) -> float:
    """Perceived luminance 0..255 for picking readable label color."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return 128.0
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.299 * r + 0.587 * g + 0.114 * b


def label_color_for(fill_hex: str, brand_dir: Path) -> str:
    """Pick a readable label color for an arbitrary fill, brand-stable.

    Uses the (off-white, chapter-slab) pair instead of (paper, ink): the
    former is guaranteed light and the latter guaranteed dark across every
    brand pack (dark brands invert ink/paper, so ink-on-ink-fill produced
    invisible labels — see fill:ink boxes in the dark-theme showcase).
    """
    return resolve("off-white", brand_dir) if relative_luminance(fill_hex) < 128 else resolve("chapter-slab", brand_dir)


def strip_brand_directive(dsl: str) -> tuple[str, str | None]:
    """Split off a leading ``@brand <name>`` directive from diagram DSL.

    Returns (cleaned_dsl, directive_or_None). The directive is the second
    whitespace-split token after ``@brand``; lines without a value are
    silently dropped along with the directive line.
    """
    directive: str | None = None
    kept: list[str] = []
    for line in dsl.splitlines():
        s = line.strip()
        if s.startswith("@brand"):
            parts = s.split(maxsplit=1)
            if len(parts) == 2:
                directive = parts[1].strip()
            continue
        kept.append(line)
    return "\n".join(kept), directive


def resolve_brand_dir(
    directive: str | None = None,
    cli_flag: str | None = None,
    deck_context: str | None = None,
    *,
    brands_root: Path | None = None,
) -> Path:
    """Pick the active brand directory by precedence:

      1. DSL @brand directive
      2. CLI --brand flag
      3. FEINSCHLIFF_BRAND env var
      4. /deck build context
      5. default 'feinschliff'

    Returns a Path that may or may not exist — callers (e.g. resolve())
    can decide how to handle missing brand dirs.
    """
    env = os.environ.get("FEINSCHLIFF_BRAND")
    chosen = directive or cli_flag or env or deck_context or "feinschliff"
    if brands_root is not None:
        return brands_root / chosen
    from lib.brand_discovery import find_brand as _find_brand
    try:
        return _find_brand(chosen).root
    except ValueError:
        raise FileNotFoundError(f"Brand {chosen!r} not found in any discovery source")
