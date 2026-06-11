"""Auto-generate layout-picker frontmatter for decompiled brand-pack layouts.

Decompiled layouts (`feinschliff-extra/brands/<brand>/layouts/*.slide.dsl`)
carry NO YAML frontmatter, so `feinschliff.layout_profile.build_profile_table`
(strict=False) silently drops every one of them — the /deck layout picker can
never choose a decompiled layout. This module closes that gap: it CLASSIFIES a
slotified layout from its DSL text alone (text slots, image slots, native
payloads) and emits the `---` frontmatter fence the picker contract requires
(`role` / `ideal_count` / `data_band` / `comparison`), plus extra keys the
parser tolerates and downstream deck planning exploits (`family`,
`fixed_chrome`, `chrome_note`, `slots`, `image_queries`, `slide_index`).

Classification heuristics — applied IN ORDER, first hit wins:

 1. slide_index == 1                          → title-primary  (framing, variety_exempt)
 2. title default / layout name ~ /agenda|inhalt|contents/i
                                              → agenda         (framing, variety_exempt)
 3. a slot default that is just a quote mark (`“`/`”`/`"`) or style:quote
                                              → quote          (voice)
 4. slide_index == total_slides, or title default ~ /thank|danke|contact|q&a$/i
                                              → closer         (closing, variety_exempt)
 5. native chart payload                      → data-comparison (comparison, data_band chart)
 6. native table payload                      → reference      (organizational, data_band table)
 7. native SmartArt payload                   → concept-diagram (process)
 8. native illustration chrome + ≤2 visible text slots
                                              → chapter-opener (framing, fixed_chrome,
                                                when_not_to_use: dense-content roles —
                                                a decorative divider must not carry facts)
 9. full-bleed image slot + ≤2 visible text slots
                                              → title-with-visual (image-driven)
10. ≥4 short body slots, ≥half numeric/percent defaults
                                              → data-quantity  (data, data_band kpi)
11. ≥3 body slots                             → content-columns (organizational)
12. otherwise                                 → content-columns (organizational)

Slot roles (per text slot, in `slots:`): page-number (1-3 digit default),
footer (bottom strip), title (largest-pt slot in the top half), eyebrow
(small text above the title), source-note (small bottom-half text), body
(everything else). Geometry thresholds assume the decompiler's 1920x1080
design space and are scaled by the declared `canvas` when it differs.

`chars` is a rough fit capacity: chars-per-line × line count from the slot's
maxwidth / maxheight box at its declared point size (0.55 em average glyph
width, 1.5 em line height).

Native-payload kind detection stays cheap and text-level: decode the carried
XML (inline `b64:` or `xml_file:` sidecar under the brand's assets root) and
look for `<c:chart` (chart), `<dgm:`/`relIds` (SmartArt), `<a:tbl` (table);
anything else — and any decode failure — is decorative `illustration` chrome.
"""
from __future__ import annotations

import base64
import math
import re
from pathlib import Path

import yaml

from feinschliff.dsl.parser import split_frontmatter

# --- DSL line patterns ------------------------------------------------------
# In the FILE the slot's inner quotes are backslash-escaped:
#   text … "{{ text_1 | default(\"Annual Review\") }}"
# The default body can never contain `"` (slotify curlifies them), so a lazy
# group terminated by `\")` is unambiguous.
_TEXT_SLOT_RE = re.compile(r'\{\{\s*(text_\d+)\s*\|\s*default\(\\"(.*?)\\"\)\s*\}\}')
_IMAGE_SLOT_RE = re.compile(r'\{\{\s*(image\d*)\s*\|\s*default\(\\"(.*?)\\"\)\s*\}\}')
_XY_RE = re.compile(r"^(?:text|picture)\s+(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)")
_WH_RE = re.compile(r"\s(-?\d+(?:\.\d+)?)x(-?\d+(?:\.\d+)?)(?:\s|$)")
_SIZE_RE = re.compile(r"\bsize:(\d+(?:\.\d+)?)pt\b")
_STYLE_RE = re.compile(r"\bstyle:([\w-]+)")
_MAXW_RE = re.compile(r"\bmaxwidth:(\d+(?:\.\d+)?)")
_MAXH_RE = re.compile(r"\bmaxheight:(\d+(?:\.\d+)?)")
_CANVAS_RE = re.compile(r"^canvas\s+(\d+)x(\d+)", re.M)
_NATIVE_RE = re.compile(r"^native\s+\w+\s+(.*)$")
_NATIVE_KW_RE = re.compile(r'(\w+):"((?:[^"\\]|\\.)*)"')

# Heuristic trigger patterns (see module docstring).
_AGENDA_RE = re.compile(r"agenda|inhalt|contents", re.I)
_CLOSER_RE = re.compile(r"thank|danke|contact|q&a$", re.I)
_QUOTE_DEFAULTS = {"“", "”", '"', "„"}
_NUMERIC_RE = re.compile(r"^[\d.,%€$+−-]+")
_PAGE_NUMBER_RE = re.compile(r"^\d{1,3}$")

# Body slots at or under this default length count as "short" for the
# data-quantity (KPI wall) heuristic — long prose can start with a digit
# without being a KPI value.
_SHORT_DEFAULT_LEN = 16

# Words that never make a useful image-search keyword: English glue plus the
# template boilerplate Microsoft layouts ship with.
_QUERY_STOPWORDS = frozenset({
    "this", "that", "with", "from", "your", "have", "will", "into", "over",
    "more", "than", "them", "then", "what", "when", "where", "which", "their",
    "there", "here", "been", "were", "also", "some", "very", "just", "only",
    "click", "edit", "master", "presentation", "headline", "placeholder",
    "lorem", "ipsum", "slide", "layout", "page", "text", "subtitle", "style",
    "styles", "title",
})


# --- DSL extraction ---------------------------------------------------------

def _parse_canvas(body: str) -> tuple[float, float]:
    m = _CANVAS_RE.search(body)
    return (float(m.group(1)), float(m.group(2))) if m else (1920.0, 1080.0)


def _parse_text_slots(body: str) -> list[dict]:
    """Each slotified `text` line → {name, default, x, y, pt, style, maxw, maxh}."""
    slots: list[dict] = []
    for line in body.splitlines():
        if not line.startswith("text "):
            continue
        m = _TEXT_SLOT_RE.search(line)
        if m is None:
            continue
        xy = _XY_RE.match(line)
        slots.append({
            "name": m.group(1),
            "default": m.group(2),
            "x": float(xy.group(1)) if xy else 0.0,
            "y": float(xy.group(2)) if xy else 0.0,
            "pt": float(_SIZE_RE.search(line).group(1)) if _SIZE_RE.search(line) else 18.0,
            "style": _STYLE_RE.search(line).group(1) if _STYLE_RE.search(line) else "",
            "maxw": float(_MAXW_RE.search(line).group(1)) if _MAXW_RE.search(line) else 400.0,
            "maxh": float(_MAXH_RE.search(line).group(1)) if _MAXH_RE.search(line) else 100.0,
        })
    return slots


def _parse_image_slots(body: str) -> list[dict]:
    """Each slotified `picture` line → {name, w, h}."""
    slots: list[dict] = []
    for line in body.splitlines():
        if not line.startswith("picture "):
            continue
        m = _IMAGE_SLOT_RE.search(line)
        if m is None:
            continue
        wh = _WH_RE.search(line.split('path:', 1)[0])
        slots.append({
            "name": m.group(1),
            "w": float(wh.group(1)) if wh else 0.0,
            "h": float(wh.group(2)) if wh else 0.0,
        })
    return slots


def _native_kind(kwargs: dict[str, str], asset_root: Path | None) -> str:
    """Cheap text-level kind sniff over a native payload's carried XML."""
    try:
        if kwargs.get("b64"):
            xml = base64.b64decode(kwargs["b64"]).decode("utf-8", "replace")
        elif kwargs.get("xml_file") and asset_root is not None:
            xml = (asset_root / kwargs["xml_file"]).read_text(
                encoding="utf-8", errors="replace")
        else:
            return "illustration"
    except Exception:
        return "illustration"
    if "graphicFrame" in xml and "<c:chart" in xml:
        return "chart"
    if "<dgm:" in xml or "relIds" in xml:
        return "smartart"
    if "<a:tbl" in xml:
        return "table"
    return "illustration"


def _parse_native_kinds(body: str, asset_root: Path | None) -> list[str]:
    kinds: list[str] = []
    for line in body.splitlines():
        m = _NATIVE_RE.match(line)
        if m is None:
            continue
        kwargs = dict(_NATIVE_KW_RE.findall(m.group(1)))
        kinds.append(_native_kind(kwargs, asset_root))
    return kinds


# --- Slot roles -------------------------------------------------------------

def _char_capacity(slot: dict) -> int:
    """Rough text capacity of the slot box (chars/line × lines), per the
    0.55 em average glyph width / 1.5 em line height rule of thumb."""
    pt_px = slot["pt"] * 96.0 / 72.0
    cols = math.floor(slot["maxw"] / (0.55 * pt_px))
    rows = max(1, math.floor(slot["maxh"] / (1.5 * pt_px)))
    return cols * rows


def _assign_slot_roles(texts: list[dict], canvas_h: float) -> dict[str, str]:
    """slot name → page-number | footer | title | eyebrow | source-note | body."""
    sy = canvas_h / 1080.0
    roles: dict[str, str] = {}
    for t in texts:
        if _PAGE_NUMBER_RE.fullmatch(t["default"].strip()):
            roles[t["name"]] = "page-number"
    for t in texts:
        if t["name"] in roles:
            continue
        if t["y"] >= 980 * sy or (t["style"] in ("body-sm", "detail")
                                  and t["y"] >= 900 * sy):
            roles[t["name"]] = "footer"
    # Title: largest-pt slot in the top half; ties break toward the top edge.
    candidates = [t for t in texts if t["name"] not in roles and t["y"] < 540 * sy]
    title = max(candidates, key=lambda t: (t["pt"], -t["y"]), default=None)
    if title is not None:
        roles[title["name"]] = "title"
    for t in texts:
        if t["name"] in roles:
            continue
        if title is not None and t["pt"] <= 18 and t["y"] < title["y"]:
            roles[t["name"]] = "eyebrow"
        elif t["y"] >= 540 * sy and t["pt"] <= 12:
            roles[t["name"]] = "source-note"
        else:
            roles[t["name"]] = "body"
    return roles


# --- Image queries ----------------------------------------------------------

def _keywords(text: str) -> list[str]:
    words = re.findall(r"[A-Za-z]+", text)
    out: list[str] = []
    for w in words:
        lw = w.lower()
        if len(lw) > 3 and lw not in _QUERY_STOPWORDS and lw not in out:
            out.append(lw)
    return out


def _image_query(layout_name: str, title_default: str) -> str:
    """2-4 lowercase search keywords for an image slot. Layered fallback:
    layout-name + title words → bare layout-name tokens → a generic query."""
    kws = _keywords(layout_name.replace("-", " ").replace("_", " ") + " "
                    + title_default.replace("\\n", " "))[:4]
    if len(kws) < 2:
        raw = [t.lower() for t in re.split(r"[^A-Za-z]+", layout_name) if t]
        kws = list(dict.fromkeys(kws + raw))[:4]
    if not kws:
        return "abstract background"
    return " ".join(kws)


# --- Classification ---------------------------------------------------------

def classify_layout(
    dsl_text: str,
    *,
    layout_name: str,
    slide_index: int,
    total_slides: int,
    asset_root: Path | None = None,
) -> dict:
    """Classify one slotified layout into its frontmatter profile dict.

    The returned dict round-trips through YAML into a fence that
    `feinschliff.layout_profile.parse_profile` accepts; the extra keys
    (`family`, `slots`, `image_queries`, …) are tolerated/ignored there and
    consumed by deck planning instead.
    """
    _, body = split_frontmatter(dsl_text)  # tolerate re-runs on profiled files
    canvas_w, canvas_h = _parse_canvas(body)
    sx, sy = canvas_w / 1920.0, canvas_h / 1080.0
    texts = _parse_text_slots(body)
    images = _parse_image_slots(body)
    native_kinds = _parse_native_kinds(body, asset_root)
    slot_roles = _assign_slot_roles(texts, canvas_h)

    title_slot = next((t for t in texts if slot_roles[t["name"]] == "title"), None)
    title_default = (title_slot or {}).get("default", "")
    body_slots = [t for t in texts if slot_roles[t["name"]] == "body"]
    n_body = len(body_slots)
    # "Visible" text = everything that is not running chrome (footer strip,
    # page number) — what a reader actually parses on the slide.
    n_visible = sum(1 for t in texts
                    if slot_roles[t["name"]] not in ("footer", "page-number"))
    full_bleed = any(i["w"] >= 1800 * sx and i["h"] >= 1000 * sy for i in images)
    kinds = set(native_kinds)

    role = "content-columns"
    family = "organizational"
    data_band = "none"
    comparison = False
    variety_exempt = False
    fixed_chrome = False
    when_not_to_use: list[str] | None = None

    short_body = [t for t in body_slots
                  if len(t["default"]) <= _SHORT_DEFAULT_LEN]
    numeric_short = [t for t in short_body if _NUMERIC_RE.match(t["default"].strip())]

    if slide_index == 1:
        role, family, variety_exempt = "title-primary", "framing", True
    elif _AGENDA_RE.search(title_default) or _AGENDA_RE.search(layout_name):
        role, family, variety_exempt = "agenda", "framing", True
    elif (any(t["default"].strip() in _QUOTE_DEFAULTS for t in texts)
          or "style:quote" in body):
        role, family = "quote", "voice"
    elif slide_index == total_slides or _CLOSER_RE.search(title_default.strip()):
        role, family, variety_exempt = "closer", "closing", True
    elif "chart" in kinds:
        role, family, data_band, comparison = (
            "data-comparison", "comparison", "chart", True)
    elif "table" in kinds:
        role, family, data_band = "reference", "organizational", "table"
    elif "smartart" in kinds:
        role, family = "concept-diagram", "process"
    elif "illustration" in kinds and n_visible <= 2:
        # Decorative divider chrome — don't put dense facts on it.
        role, family, fixed_chrome = "chapter-opener", "framing", True
        when_not_to_use = [
            "role=content-columns", "role=data-quantity", "role=data-comparison",
        ]
    elif full_bleed and n_visible <= 2:
        role, family = "title-with-visual", "image-driven"
    elif (len(short_body) >= 4
          and len(numeric_short) * 2 >= len(short_body)):
        role, family, data_band = "data-quantity", "data", "kpi"
    elif n_body >= 3:
        role, family = "content-columns", "organizational"

    if role in ("title-primary", "chapter-opener", "quote", "closer"):
        ideal_count = [1, 2]
    else:
        lo = max(1, n_body)
        ideal_count = [lo, max(n_body, lo)]

    profile: dict = {
        "role": role,
        "ideal_count": ideal_count,
        "data_band": data_band,
        "comparison": comparison,
    }
    if variety_exempt:
        profile["variety_exempt"] = True
    if when_not_to_use:
        profile["when_not_to_use"] = when_not_to_use
    profile["family"] = family
    if fixed_chrome:
        profile["fixed_chrome"] = True
    if native_kinds:
        counts = {k: native_kinds.count(k) for k in sorted(kinds)}
        profile["chrome_note"] = (
            "carries native source chrome verbatim: "
            + ", ".join(f"{n} {k}" for k, n in counts.items())
        )
    profile["slide_index"] = slide_index
    if texts:
        profile["slots"] = {
            t["name"]: {
                "role": slot_roles[t["name"]],
                "chars": _char_capacity(t),
                # Preview only — truncated so a lorem paragraph cannot bloat
                # the frontmatter; the authoritative default stays in the DSL.
                "default": (t["default"][:77] + "…"
                            if len(t["default"]) > 78 else t["default"]),
            }
            for t in texts
        }
    if images:
        query = _image_query(layout_name, title_default)
        profile["image_queries"] = {i["name"]: query for i in images}
    return profile


# --- Frontmatter application ------------------------------------------------

def _strip_fence(dsl_text: str) -> str:
    """Drop a leading `--- … ---` fence (preceded only by blank lines),
    returning everything after it byte-identical. No fence → text unchanged."""
    lines = dsl_text.splitlines(keepends=True)
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or lines[i].strip() != "---":
        return dsl_text
    for j in range(i + 1, len(lines)):
        if lines[j].strip() == "---":
            return "".join(lines[j + 1:])
    return dsl_text  # unterminated fence — leave the document alone


def apply_profile(dsl_text: str, profile: dict) -> str:
    """Prepend (or replace) the YAML frontmatter fence; the body after the
    fence stays byte-identical, so re-running the generator is idempotent."""
    fm = yaml.safe_dump(profile, sort_keys=False, allow_unicode=True,
                        default_flow_style=None, width=120)
    return "---\n" + fm + "---\n" + _strip_fence(dsl_text)


# --- Deck map ---------------------------------------------------------------

def derive_deck_map(profiles: dict[str, dict]) -> dict:
    """Reduce `{layout_name: profile}` to the deck-planning role map written
    to `<brand>/deck-map.yaml`: one cover/agenda/quote/closer, the
    chapter-opener section dividers, and everything else as content in slide
    order. Keys without a matching layout are omitted (except `content`)."""
    def idx(name: str) -> int:
        return int(profiles[name].get("slide_index", 10 ** 9))

    ordered = sorted(profiles, key=lambda n: (idx(n), n))
    by_role: dict[str, list[str]] = {}
    for name in ordered:
        by_role.setdefault(profiles[name]["role"], []).append(name)

    deck_map: dict = {}
    used: set[str] = set()
    covers = by_role.get("title-primary", [])
    if covers:
        deck_map["cover"] = covers[0]  # lowest slide index wins
        used.add(covers[0])
    agendas = by_role.get("agenda", [])
    if agendas:
        deck_map["agenda"] = agendas[0]
        used.add(agendas[0])
    sections = by_role.get("chapter-opener", [])
    if sections:
        deck_map["section"] = sections
        used.update(sections)
    quotes = by_role.get("quote", [])
    if quotes:
        deck_map["quote"] = quotes[0]
        used.add(quotes[0])
    closers = by_role.get("closer", [])
    if closers:
        deck_map["closer"] = closers[-1]  # highest slide index wins
        used.add(closers[-1])
    deck_map["content"] = [n for n in ordered if n not in used]
    return deck_map
