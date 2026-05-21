"""Token loader + resolver, including brief-defaults helper.

A brand pack ships a `tokens.json` (the existing v1 schema is fine for PoC).
Optional `DESIGN.md` frontmatter may declare `extends: <parent-brand>` to
inherit and selectively override.

  brand_pack/
    DESIGN.md          # frontmatter with extends + override notes
    tokens.json        # color / font-family / font-weight / font-size / slide
    compounds/*.dsl    # brand-specific compounds

Style refs in DSL (`style:eyebrow`) resolve here. A style is a *bundle* of
font-family + size + weight + color, looked up by name in tokens.json or
inherited from a parent brand. The bundle is built lazily from the role
name following the existing convention:

  style:title       -> font-family.display, font-size.slide-title,  weight.semibold, color.ink
  style:body        -> font-family.body,    font-size.body,         weight.regular,  color.graphite
  style:eyebrow     -> font-family.mono,    font-size.eyebrow,      weight.medium,   color.steel
  style:kpi-value   -> font-family.display, font-size.kpi-value,    weight.bold,     color.ink
  ...

The bundle defaults live in `STYLE_BUNDLES`; brands can override any field
via `tokens.json` -> `style: { <name>: {...} }` (forward-compatible -- not
required for PoC).

Fill refs (`fill:accent`, `stroke:fog`) resolve directly to the color
token of that name.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from feinschliff.jsonwalk import deep_merge


_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "tokens.schema.json"

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _is_hex_literal(s: str) -> bool:
    return bool(_HEX_RE.match(s))


def _expand_short_hex(s: str) -> str:
    # `#abc` → `#aabbcc`
    return "#" + "".join(ch * 2 for ch in s[1:])


def _strip_px(v: Any, key: str, brand_name: str) -> float:
    """Coerce a px-valued token to float. Accepts a bare number (assumed px)
    or a string ending in `"px"`. Raises ValueError on any other unit
    (`"1.5rem"`, `"12em"`) — silent acceptance would crash deeper in the
    emitter with a much less useful traceback.
    """
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if s.endswith("px"):
        return float(s[:-2])
    # Accept a bare numeric string too (no unit) — common in tokens.json.
    try:
        return float(s)
    except ValueError:
        raise ValueError(
            f"brand '{brand_name}': token '{key}' has value '{v}' — "
            f"expected a number in px (e.g. '24px' or 24). Other CSS units "
            f"are not supported in v2 tokens."
        ) from None


def _load_tokens_schema() -> dict[str, Any]:
    return json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))


def validate_tokens(merged: dict[str, Any], brand_name: str) -> None:
    """Validate a merged tokens dict against tokens.schema.json. Raises ValueError on failure."""
    validator = Draft202012Validator(_load_tokens_schema())
    errors = sorted(validator.iter_errors(merged), key=lambda e: list(e.absolute_path))
    if not errors:
        return
    parts = [f"brand '{brand_name}': tokens.json validation failed (schema: {_SCHEMA_PATH}):"]
    for err in errors:
        loc = ".".join(str(p) for p in err.absolute_path) or "<root>"
        parts.append(f"  - {loc}: {err.message}")
    raise ValueError("\n".join(parts))


# Standard style bundles. Keys match the role tokens in tokens.json's
# font-size map. Brands can override the bundle in tokens.json under a
# top-level `style` key (not used in PoC).
STYLE_BUNDLES: dict[str, dict[str, Any]] = {
    # Element-role bundles. font-size keys must exist in tokens.json.font-size;
    # color keys must exist in tokens.json.color.
    # Optional keys per bundle:
    #   transform: "upper" → uppercase text at emit time (canonical .eyebrow rule)
    #   opacity:   0..1     → text opacity (canonical .pgmeta rule, opacity 0.7)
    #
    # Bindings tuned against feinschliff canonical CSS:
    "title":       {"font": "display", "size": "slide-title", "weight": "bold",     "color": "ink", "letter_spacing": -0.015, "line_height": 1.1},
    # Larger slide title for brands that author at ~80px (e.g. gs-ramspau).
    "title-l":     {"font": "display", "size": "title-l",     "weight": "bold",     "color": "ink", "letter_spacing": -0.02, "line_height": 1.05},
    "sub":         {"font": "display", "size": "sub",         "weight": "regular",  "color": "graphite"},
    "huge":        {"font": "display", "size": "huge",        "weight": "light",    "color": "ink", "line_height": 0.95},
    # Canonical .display class — 160px light w/ tight tracking + 0.95 line-height.
    "display":     {"font": "display", "size": "display",     "weight": "light",    "color": "ink", "letter_spacing": -0.035, "line_height": 0.95},
    # 200px inline-override used by the end-slide "Thank you." headline.
    "display-xl":  {"font": "display", "size": "display-xl",  "weight": "light",    "color": "ink", "letter_spacing": -0.035, "line_height": 0.95},
    # Ghosted big-number marks. Color is canonical ink; callers override via color:.
    "bignum":      {"font": "display", "size": "bignum",       "weight": "light",    "color": "ink", "letter_spacing": -0.04, "line_height": 0.85},
    # Column-card sub-elements — `.col-t` is font-weight 500 (medium), NOT bold.
    "col-num":     {"font": "mono",    "size": "col-num",     "weight": "regular",  "color": "accent",   "transform": "upper"},
    "col-title":   {"font": "display", "size": "col-title",   "weight": "medium",   "color": "ink", "letter_spacing": -0.012, "line_height": 1.15},
    "col-title-q": {"font": "display", "size": "col-title-q", "weight": "medium",   "color": "ink", "letter_spacing": -0.012, "line_height": 1.15},
    "col-body":    {"font": "body",    "size": "col-body",    "weight": "regular",  "color": "graphite"},
    "rule":        {"font": "display", "size": "footer",      "weight": "regular",  "color": "ink"},
    "body":        {"font": "body",    "size": "body",        "weight": "regular",  "color": "graphite"},
    # Small-body — 16px sans, the classifier in pptx_svg_decompile.py emits
    # this for ≤12pt source text (dense table cells, source credits, fine
    # print). Reuses the `footer` size token (16px) so brands don't need to
    # declare an extra font-size key.
    "body-sm":     {"font": "body",    "size": "footer",      "weight": "regular",  "color": "graphite"},
    # Chrome — canonical eyebrow, footer, pgmeta all uppercase mono. pgmeta is
    # also dimmed (CSS opacity 0.7); footer + eyebrow inherit full body color.
    "eyebrow":     {"font": "mono",    "size": "eyebrow",     "weight": "regular",  "color": "ink",      "transform": "upper"},
    "footer":      {"font": "mono",    "size": "footer",      "weight": "regular",  "color": "graphite", "transform": "upper"},
    "pgmeta":      {"font": "mono",    "size": "pgmeta",      "weight": "regular",  "color": "ink",      "transform": "upper", "opacity": 0.7},
    "kpi-value":   {"font": "display", "size": "kpi-value",   "weight": "light",    "color": "ink", "letter_spacing": -0.03, "line_height": 0.95},
    "kpi-unit":    {"font": "display", "size": "kpi-unit",    "weight": "light",    "color": "graphite"},
    "kpi-key":     {"font": "mono",    "size": "kpi-key",     "weight": "regular",  "color": "graphite", "transform": "upper", "letter_spacing": 0.1},
    "kpi-delta":   {"font": "mono",    "size": "kpi-delta",   "weight": "regular",  "color": "accent-hover"},
    "agenda-num":  {"font": "mono",    "size": "agenda-num",  "weight": "medium",   "color": "accent",   "transform": "upper"},
    "agenda-t":    {"font": "display", "size": "agenda-t",    "weight": "semibold", "color": "ink"},
    "agenda-d":    {"font": "body",    "size": "agenda-d",    "weight": "regular",  "color": "graphite"},
    "quote":       {"font": "display", "size": "quote",       "weight": "light",    "color": "ink", "letter_spacing": -0.025, "line_height": 1.1},
    "quote-attr":  {"font": "mono",    "size": "quote-attr",  "weight": "regular",  "color": "graphite", "transform": "upper"},
    "quote-glyph": {"font": "display", "size": "huge",        "weight": "light",    "color": "accent"},
    "brand-mark":  {"font": "display", "size": "footer",      "weight": "bold",     "color": "ink"},
    "wordmark":    {"font": "display", "size": "pgmeta",      "weight": "medium",   "color": "ink",      "transform": "upper", "letter_spacing": 0.1},
    # Button label — canonical .btn is 22px medium.
    "btn":         {"font": "display", "size": "btn",         "weight": "medium",   "color": "ink"},
    # Chip — sample component, mono caps small.
    "chip":        {"font": "mono",    "size": "chip",        "weight": "medium",   "color": "ink", "transform": "upper", "letter_spacing": 0.08},
    "detail":      {"font": "mono",    "size": "footer",      "weight": "regular",  "color": "steel"},
    # MCK / action-title family.
    "act-title":   {"font": "display", "size": "act-title",   "weight": "regular",  "color": "ink", "letter_spacing": -0.02, "line_height": 1.1},
    "act-kicker":  {"font": "mono",    "size": "act-kicker",  "weight": "regular",  "color": "ink", "transform": "upper", "letter_spacing": 0.12},
    "tracker":     {"font": "mono",    "size": "tracker",     "weight": "regular",  "color": "graphite", "transform": "upper", "letter_spacing": 0.12},
    "h-idx":       {"font": "mono",    "size": "h-idx",       "weight": "regular",  "color": "accent-hover", "transform": "upper", "letter_spacing": 0.14},
    "h-hd":        {"font": "display", "size": "h-hd",        "weight": "medium",   "color": "ink", "letter_spacing": -0.012, "line_height": 1.15},
    "h-li":        {"font": "body",    "size": "h-li",        "weight": "regular",  "color": "graphite", "line_height": 1.45},
    "lede":        {"font": "display", "size": "lede",        "weight": "light",    "color": "ink", "letter_spacing": -0.015, "line_height": 1.2},
}


@dataclass
class ResolvedStyle:
    font_family: list[str]
    size_px: float                   # design pixels at 1920×1080 canvas
    weight: int                      # 100..900
    color_hex: str                   # "#RRGGBB"
    transform: str | None = None     # None or "upper"
    opacity: float = 1.0             # 0.0..1.0 (multiplied into color at emit time)
    letter_spacing: float = 0.0      # em fraction (e.g. 0.1 = 10% letter-spacing)
    line_height: float = 1.2         # paragraph line-height multiplier (CSS line-height)
    color_role: str = "ink"          # token role name (preserved for hierarchy stepping)


@dataclass
class Tokens:
    """Resolved token bundle for one brand. Parent inheritance already
    flattened. Lookup by role name returns a ResolvedStyle."""
    raw: dict[str, Any]              # the fully-merged tokens.json dict
    brand_name: str

    # Layer 1 typography / picture / locale tokens — populated from `raw`
    # in __post_init__ so callers that construct via load_tokens get them
    # transparently. Defaults match an unset brand.
    display_tracking_curve: dict[int, float] = field(default_factory=dict)
    tnum_font: str | None = None
    tnum_slot_keys: set[str] = field(default_factory=set)
    picture_treatment: str = "none"
    locale: str = "en"

    # Layer 1 chart-sanitation tokens (read by Layer 2 chart layouts).
    chart_chrome: str = "minimal"
    chart_axis_color_role: str = "neutral-faint"
    chart_legend_threshold: int = 4

    def __post_init__(self) -> None:
        typography = self.raw.get("typography", {}) or {}
        curve_raw = typography.get("display_tracking_curve", {}) or {}
        if curve_raw and not self.display_tracking_curve:
            self.display_tracking_curve = {int(k): float(v) for k, v in curve_raw.items()}
        if self.tnum_font is None:
            self.tnum_font = typography.get("tnum_font")
        slot_keys_raw = typography.get("tnum_slot_keys")
        if slot_keys_raw and not self.tnum_slot_keys:
            self.tnum_slot_keys = set(slot_keys_raw)

        if self.picture_treatment == "none":
            self.picture_treatment = self.raw.get("picture_treatment", "none")
        if self.locale == "en":
            self.locale = self.raw.get("locale", "en")

        chart = self.raw.get("chart", {}) or {}
        if self.chart_chrome == "minimal":
            self.chart_chrome = chart.get("chrome", "minimal")
        if self.chart_axis_color_role == "neutral-faint":
            self.chart_axis_color_role = chart.get("axis_color_role", "neutral-faint")
        legend = chart.get("legend_threshold")
        if legend is not None:
            self.chart_legend_threshold = int(legend)

    @classmethod
    def from_dict(cls, raw: dict[str, Any], *, brand_name: str) -> Tokens:
        """Construct a Tokens bundle from an already-merged dict. Test-friendly
        — skips strict tokens.schema.json validation (use `load_tokens` for
        on-disk brand packs that need schema enforcement)."""
        return cls(raw=raw, brand_name=brand_name)

    # --- public lookups -----------------------------------------------

    def color(self, name: str) -> str:
        if isinstance(name, str) and name.startswith("#") and _is_hex_literal(name):
            # Inline hex passthrough — the decompiler emits raw `#RRGGBB`
            # for shape fills the reverse-token-mapping pass couldn't
            # resolve. Treat them as valid colours so the verify loop can
            # build the slide without forcing every literal into the
            # brand's palette.
            return name.upper() if len(name) == 7 else _expand_short_hex(name).upper()
        colors = self.raw.get("color", {})
        c = colors.get(name)
        if c is None:
            # chart-series ramp fallback — matches the same convention
            # `brand_bridge.resolve()` applies for the diagram DSL.
            # Brands that don't ship an explicit per-series tint
            # progression render every series in the brand's accent hue;
            # bar/pie chart decks still build instead of crashing the
            # whole layout with KeyError.
            if isinstance(name, str) and name.startswith("chart-series-"):
                fallback = colors.get("accent")
                if fallback is not None:
                    return fallback["$value"] if isinstance(fallback, dict) else fallback
            raise KeyError(f"brand '{self.brand_name}': no color token '{name}'")
        if isinstance(c, dict):           # designtokens schema: {"$value": "..."}
            return c["$value"]
        return c

    def font_family(self, name: str) -> list[str]:
        f = self.raw.get("font-family", {}).get(name)
        if f is None:
            raise KeyError(f"brand '{self.brand_name}': no font-family '{name}'")
        if isinstance(f, dict):
            return list(f["$value"])
        return list(f)

    def font_size_px(self, name: str) -> float:
        f = self.raw.get("font-size", {}).get(name)
        if f is None:
            raise KeyError(f"brand '{self.brand_name}': no font-size '{name}'")
        if isinstance(f, dict):
            v = f["$value"]
        else:
            v = f
        return _strip_px(v, f"font-size.{name}", self.brand_name)

    def font_weight(self, name: str) -> int:
        f = self.raw.get("font-weight", {}).get(name)
        if f is None:
            # Standard fallback weights match CSS conventions.
            return {"light": 300, "regular": 400, "medium": 500,
                    "semibold": 600, "bold": 700, "black": 900}.get(name, 400)
        if isinstance(f, dict):
            return int(f["$value"])
        return int(f)

    def slide(self, key: str) -> float:
        s = self.raw.get("slide", {}).get(key)
        if s is None:
            # Sane defaults for the 1920×1080 canvas.
            return {"width": 1920, "height": 1080,
                    "padding-x": 100, "padding-y-top": 100,
                    "padding-y-bottom": 80}.get(key, 0)
        if isinstance(s, dict):
            s = s["$value"]
        return _strip_px(s, f"slide.{key}", self.brand_name)

    # --- style-bundle resolver ----------------------------------------

    def resolve_style(self, name: str) -> ResolvedStyle:
        bundle = STYLE_BUNDLES.get(name)
        override = self.raw.get("style", {}).get(name) or {}
        # Brand-level overrides: tokens.json can declare a top-level `style`
        # map keyed by bundle name, where each value is either:
        #   (a) a partial override merged on top of an existing canonical
        #       STYLE_BUNDLES entry, OR
        #   (b) a full brand-defined style under a new name (used when one
        #       logical token needs distinct sizes/weights across chrome
        #       regions, e.g. wordmark large on covers vs. small in footer).
        # A `transform` override may set null to clear the canonical
        # transform (e.g. mixed-case eyebrow). The schema reserves this
        # top-level key under `lib/schemas/tokens.schema.json`.
        if bundle is None:
            required = {"font", "size", "weight", "color"}
            missing = required - override.keys()
            if missing:
                known = sorted(set(STYLE_BUNDLES.keys()) |
                               set(self.raw.get("style", {}).keys()))
                raise KeyError(
                    f"unknown style '{name}' (brand override missing "
                    f"{sorted(missing)}). Known: {known}"
                )
            bundle = override
        bundle = {**bundle, **override}
        return ResolvedStyle(
            font_family=self.font_family(bundle["font"]),
            size_px=self.font_size_px(bundle["size"]),
            weight=self.font_weight(bundle["weight"]),
            color_hex=self.color(bundle["color"]),
            transform=bundle.get("transform"),
            opacity=float(bundle.get("opacity", 1.0)),
            letter_spacing=float(bundle.get("letter_spacing", 0.0)),
            line_height=float(bundle.get("line_height", 1.2)),
            color_role=bundle["color"],
        )


# ---------------------------------------------------------------------------
# Brand pack loading
# ---------------------------------------------------------------------------

def _parse_design_md_frontmatter(text: str) -> dict[str, Any]:
    """Extract YAML frontmatter from a DESIGN.md. Returns {} if absent."""
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    import yaml
    return yaml.safe_load(text[3:end]) or {}


def load_tokens(brand_root: Path, *, brands_dir: Path | None = None) -> Tokens:
    """Load a brand's tokens.json, flattening any `extends: <parent>` chain
    declared in DESIGN.md frontmatter. `brands_dir` defaults to the parent
    of `brand_root`.
    """
    brands_dir = brands_dir or brand_root.parent
    chain: list[Path] = []
    visited: set[str] = set()
    cur = brand_root
    while True:
        if cur.name in visited:
            raise ValueError(f"cyclic brand inheritance through {cur.name}")
        visited.add(cur.name)
        chain.append(cur)
        design = cur / "DESIGN.md"
        parent_name = None
        if design.is_file():
            fm = _parse_design_md_frontmatter(design.read_text())
            parent_name = fm.get("extends")
        if not parent_name:
            # `extends:` is a DESIGN.md-frontmatter convention; it has never
            # been read from tokens.json. But putting it in tokens.json is a
            # natural mistake (DTCG-flavoured packs put everything there),
            # and the resulting failure mode is misleading — the child pack
            # is treated as standalone, parent keys never merge, and
            # validation dies with "'font-size' is a required property" or
            # similar. Surface the misplacement explicitly.
            tj = cur / "tokens.json"
            if tj.is_file():
                try:
                    raw = json.loads(tj.read_text())
                except json.JSONDecodeError:
                    raw = {}
                if isinstance(raw, dict) and "extends" in raw:
                    raise ValueError(
                        f"brand '{cur.name}': tokens.json has an `extends` "
                        f"key, but `extends` must be declared in DESIGN.md "
                        f"frontmatter (`---\\nextends: <parent>\\n---`). "
                        f"The tokens.json entry is silently ignored, which "
                        f"is why required keys like font-size appear missing."
                    )
            break
        parent = brands_dir / parent_name
        if not parent.is_dir():
            # Cross-plugin extends: a brand in feinschliff-extra/brands/
            # commonly extends `feinschliff` which lives in the core plugin's
            # brands/ — a different brands_dir. Walk the same discovery
            # sources brand_discovery scans, but stop at the path layer so
            # we don't re-enter load_tokens (discover_brands() calls
            # load_tokens for image_provider resolution → recursion).
            from feinschliff.brand_discovery import _discovery_sources
            parent = None
            for _src, root in _discovery_sources():
                cand = root / parent_name
                if cand.is_dir():
                    parent = cand
                    brands_dir = root
                    break
            if parent is None:
                raise FileNotFoundError(
                    f"brand '{cur.name}' extends '{parent_name}' but not "
                    f"found in {brands_dir} or via plugin discovery"
                )
        cur = parent

    merged: dict[str, Any] = {}
    # parents first → child last (so child overrides win)
    for b in reversed(chain):
        tj = b / "tokens.json"
        if tj.is_file():
            data = json.loads(tj.read_text())
            # `$image_provider` semantics: when the child swaps `kind`, the
            # parent's `config` must NOT carry over (it was scoped to a
            # different provider). Drop merged's `config` before deep-merge
            # so the child can declare a kind-only override cleanly. The
            # standard deep_merge already handles the same-kind case where
            # the child only refines `config` keys.
            #
            # Today `$image_provider` only carries `kind` + `config`, but we
            # drop ONLY `config` (the provider-scoped key) rather than the
            # whole parent block so any future top-level keys (`enabled`,
            # `fallback`, …) survive a kind-swap. If you add such a key,
            # audit this block and decide whether it's provider-scoped.
            child_ip = data.get("$image_provider") if isinstance(data, dict) else None
            parent_ip = merged.get("$image_provider")
            if (
                isinstance(child_ip, dict)
                and isinstance(parent_ip, dict)
                and "kind" in child_ip
                and child_ip.get("kind") != parent_ip.get("kind")
            ):
                new_parent_ip = {k: v for k, v in parent_ip.items() if k != "config"}
                merged = {**merged, "$image_provider": new_parent_ip}
            merged = deep_merge(merged, data)
    validate_tokens(merged, brand_root.name)
    return Tokens(raw=merged, brand_name=brand_root.name)


# Allowed keys in brief_defaults — mirrors the schema enum constraints.
_BRIEF_DEFAULTS_KNOWN_KEYS: frozenset[str] = frozenset(
    {"verbosity", "image_style", "frame", "audience"}
)


def load_brief_defaults(brand_dir: Path) -> dict[str, str]:
    """Read brief_defaults from <brand_dir>/tokens.json.

    Returns {} if the brand has no brief_defaults block (back-compat for brands
    that haven't set any priors). If the file is missing, also returns {}.

    Unknown keys in brief_defaults emit a stderr warning but are included in
    the returned dict so callers can inspect them without a hard failure.
    """
    tokens_file = brand_dir / "tokens.json"
    if not tokens_file.is_file():
        return {}
    raw = json.loads(tokens_file.read_text(encoding="utf-8"))
    defaults: dict[str, Any] = raw.get("brief_defaults") or {}
    if not isinstance(defaults, dict):
        return {}
    unknown = set(defaults.keys()) - _BRIEF_DEFAULTS_KNOWN_KEYS
    if unknown:
        print(
            f"WARNING: brand '{brand_dir.name}' brief_defaults contains unknown "
            f"key(s): {sorted(unknown)}. Known: {sorted(_BRIEF_DEFAULTS_KNOWN_KEYS)}",
            file=sys.stderr,
        )
    return dict(defaults)
