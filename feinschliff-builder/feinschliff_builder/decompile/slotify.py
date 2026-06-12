"""Slotify pass over decompiled `.slide.dsl` layouts.

The hybrid decompiler emits slide-faithful layouts whose text is LITERAL —
right for measuring decompile fidelity, useless as a fillable template. This
pass rewrites every literal text label into

    text … "{{ text_N | default(\"<original literal>\") }}"

so the layout becomes a real template: a bare build (empty ctx) renders the
original showcase copy via the `default(…)` filter, and a deck build binds
`text_1..text_N` in ctx to replace it. Picture placeholders are already
slotified at decompile time (`path:"{{ image | default(\"…\") }}"`); native
chrome (logos, custGeom decoration) intentionally stays fixed.

Grammar constraints honoured (see feinschliff/dsl/expander.py):
  * `_DEFAULT_FILTER_RE` allows no ASCII `"` inside default("…") — escaped
    quotes in the source literal are typographically curlified (“…”).
  * `_SLOT_RE` bodies cannot contain `{`/`}` — labels with braces stay
    literal rather than emitting a slot that cannot parse.

Slot numbering is per-file, in line order: text_1, text_2, …
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# A top-level text primitive whose trailing bare-quoted token is the label.
# Group 1 = everything up to the opening quote, group 2 = raw escaped label.
_TEXT_LINE_RE = re.compile(r'^(text\b[^"]*)"((?:[^"\\]|\\.)*)"\s*$')

# --- Geometry helpers (shared with layout_profile_gen) ----------------------

# X,Y and WxH patterns for `picture` and slot-bearing `text` lines.
_GEO_XY_RE = re.compile(r"^(?:text|picture)\s+(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)")
_GEO_WH_RE = re.compile(r"\s(-?\d+(?:\.\d+)?)x(-?\d+(?:\.\d+)?)(?:\s|$)")
_GEO_MAXW_RE = re.compile(r"\bmaxwidth:(\d+(?:\.\d+)?)")
_GEO_MAXH_RE = re.compile(r"\bmaxheight:(\d+(?:\.\d+)?)")
_GEO_TEXT_SLOT_RE = re.compile(r"\{\{\s*(text_\d+)\s*\|")
_GEO_IMAGE_SLOT_RE = re.compile(r"\{\{\s*image\w*\s*\|")

# Overlaps must exceed this many design-px on BOTH axes to count — kissing
# edges and 1-2 px decompile jitter are not collisions.
IMAGE_OVERLAP_EPSILON = 8.0


def crosses_image_edge(t: dict, img: dict) -> bool:
    """True when a text box PARTIALLY overlaps a picture box.

    A text box fully inside the picture is an intentional overlay
    (chapter openers, captions on photos) and returns False.

    ``t``   — {x, y, maxw, maxh} text descriptor.
    ``img`` — {x, y, w, h} picture descriptor.

    Exported publicly so layout_profile_gen can import it.
    """
    ix0, iy0 = img["x"], img["y"]
    ix1, iy1 = ix0 + img["w"], iy0 + img["h"]
    tx0, ty0 = t["x"], t["y"]
    tx1, ty1 = tx0 + t["maxw"], ty0 + t["maxh"]
    overlap_w = min(tx1, ix1) - max(tx0, ix0)
    overlap_h = min(ty1, iy1) - max(ty0, iy0)
    if overlap_w <= IMAGE_OVERLAP_EPSILON or overlap_h <= IMAGE_OVERLAP_EPSILON:
        return False
    contained = (
        tx0 >= ix0 - IMAGE_OVERLAP_EPSILON
        and ty0 >= iy0 - IMAGE_OVERLAP_EPSILON
        and tx1 <= ix1 + IMAGE_OVERLAP_EPSILON
        and ty1 <= iy1 + IMAGE_OVERLAP_EPSILON
    )
    return not contained


# Gutter kept between a clipped text box and the picture edge (design-px).
_CLIP_GUTTER = 16.0
# Minimum useful width / height after a clip; below this the clip is skipped
# (TEXT_OVER_IMAGE warning in the profile covers the warn-only case).
_CLIP_MIN_W = 200.0   # narrower than this is not a usable text column
_CLIP_MIN_H = 60.0    # shorter than this is not a usable text box


def _parse_pictures_for_clip(dsl_text: str) -> list[dict]:
    """Parse `picture` lines that carry an image slot into geometry dicts."""
    pics: list[dict] = []
    for line in dsl_text.splitlines():
        if not line.startswith("picture "):
            continue
        if not _GEO_IMAGE_SLOT_RE.search(line):
            continue
        xy = _GEO_XY_RE.match(line)
        # geometry precedes the path: keyword — chop it off to avoid matching
        # e.g. "1920x1080" in the path string.
        prefix = line.split("path:", 1)[0]
        wh = _GEO_WH_RE.search(prefix)
        if xy is None or wh is None:
            continue
        m_name = re.search(r"\{\{\s*(\w+)\s*\|", line)
        pics.append({
            "name": m_name.group(1) if m_name else "?",
            "x": float(xy.group(1)), "y": float(xy.group(2)),
            "w": float(wh.group(1)), "h": float(wh.group(2)),
            "_line": line,
        })
    return pics


def _parse_slot_texts_for_clip(dsl_text: str) -> list[dict]:
    """Parse slot-bearing `text` lines into geometry + name dicts."""
    texts: list[dict] = []
    for line in dsl_text.splitlines():
        if not line.startswith("text "):
            continue
        m = _GEO_TEXT_SLOT_RE.search(line)
        if m is None:
            continue
        xy = _GEO_XY_RE.match(line)
        mw = _GEO_MAXW_RE.search(line)
        mh = _GEO_MAXH_RE.search(line)
        if xy is None or mw is None or mh is None:
            continue
        texts.append({
            "name": m.group(1),
            "x": float(xy.group(1)), "y": float(xy.group(2)),
            "maxw": float(mw.group(1)), "maxh": float(mh.group(1)),
            "_line": line,
        })
    return texts


def _fmt_num(v: float) -> str:
    """Format a geometry number: integral when whole, :g otherwise."""
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def clip_text_to_images(dsl_text: str) -> tuple[str, list[str]]:
    """Shrink slot-bearing text boxes that cross a picture slot's edge so the
    box ends at the image boundary (with a small gutter).

    Never moves the origin; only shrinks ``maxwidth`` (image to the right) or
    ``maxheight`` (image below). When the origin itself sits inside a picture,
    or the remainder would be unusably narrow/short, the box is left alone —
    the TEXT_OVER_IMAGE pack warning in the profile covers it.

    Returns ``(new_dsl, [log lines])``.  Log lines have the form::

        text_3: maxwidth 1835 -> 915 (clipped at picture 'image2')

    Idempotent: a clipped box no longer crosses the edge -> second run is a no-op.
    """
    pics = _parse_pictures_for_clip(dsl_text)
    if not pics:
        return dsl_text, []

    texts = _parse_slot_texts_for_clip(dsl_text)
    if not texts:
        return dsl_text, []

    # Build a mapping: original line text -> replacement line text.
    replacements: dict[str, str] = {}  # original line -> rewritten line
    logs: list[str] = []

    for t in texts:
        current = dict(t)  # mutable copy - updated by successive picture clips
        current_line = t["_line"]

        for pic in pics:
            if not crosses_image_edge(current, pic):
                continue

            ix0 = pic["x"]
            iy0 = pic["y"]
            tx0, ty0 = current["x"], current["y"]

            # Only clip when origin is OUTSIDE the picture on the candidate axis.
            can_clip_w = tx0 < ix0 - IMAGE_OVERLAP_EPSILON
            can_clip_h = ty0 < iy0 - IMAGE_OVERLAP_EPSILON

            clip_axis: str | None = None
            new_val: float = 0.0
            old_val: float = 0.0

            if can_clip_w and can_clip_h:
                # Both axes possible — pick the one that preserves more area.
                new_w = ix0 - tx0 - _CLIP_GUTTER
                new_h = iy0 - ty0 - _CLIP_GUTTER
                if new_w * current["maxh"] >= current["maxw"] * new_h:
                    clip_axis, new_val, old_val = "w", new_w, current["maxw"]
                else:
                    clip_axis, new_val, old_val = "h", new_h, current["maxh"]
            elif can_clip_w:
                clip_axis = "w"
                new_val = ix0 - tx0 - _CLIP_GUTTER
                old_val = current["maxw"]
            elif can_clip_h:
                clip_axis = "h"
                new_val = iy0 - ty0 - _CLIP_GUTTER
                old_val = current["maxh"]
            else:
                # Origin inside picture on both candidate axes -> warn-only.
                continue

            # Usability guards.
            if clip_axis == "w":
                if new_val < max(_CLIP_MIN_W, 0.25 * current["maxw"]):
                    continue  # too narrow — skip
            else:
                if new_val < max(_CLIP_MIN_H, 0.25 * current["maxh"]):
                    continue  # too short — skip

            if clip_axis == "w":
                new_line = _GEO_MAXW_RE.sub(
                    f"maxwidth:{_fmt_num(new_val)}", current_line, count=1)
                logs.append(
                    f"{current['name']}: maxwidth {_fmt_num(old_val)} -> {_fmt_num(new_val)}"
                    f" (clipped at picture '{pic['name']}')"
                )
                current["maxw"] = new_val
            else:
                new_line = _GEO_MAXH_RE.sub(
                    f"maxheight:{_fmt_num(new_val)}", current_line, count=1)
                logs.append(
                    f"{current['name']}: maxheight {_fmt_num(old_val)} -> {_fmt_num(new_val)}"
                    f" (clipped at picture '{pic['name']}')"
                )
                current["maxh"] = new_val

            replacements[current_line] = new_line
            current_line = new_line  # for subsequent picture iterations

    if not replacements:
        return dsl_text, []

    # Apply replacements line-by-line (exact string match is safe because
    # every DSL line is unique in practice).
    out_lines: list[str] = []
    for line in dsl_text.splitlines(keepends=True):
        stripped = line.rstrip("\n")
        if stripped in replacements:
            repl = replacements[stripped]
            out_lines.append(repl + ("\n" if line.endswith("\n") else ""))
        else:
            out_lines.append(line)
    return "".join(out_lines), logs


def _curlify(raw: str) -> str:
    r"""Replace escaped ASCII quotes (`\"`) in a raw DSL literal with curly
    quotes so the literal can ride inside the expander's default("…") filter.
    Literal backslashes (`\\`) are protected first, mirroring the parser's
    `_unquote` ordering. Opening/closing forms alternate per run of text."""
    protected = raw.replace("\\\\", "\x00")
    out: list[str] = []
    open_next = True
    for chunk in protected.split('\\"'):
        out.append(chunk)
        out.append("“" if open_next else "”")
        open_next = not open_next
    s = "".join(out[:-1])  # drop the trailing quote added after the last chunk
    return s.replace("\x00", "\\\\")


def slotify_dsl(dsl_text: str) -> tuple[str, list[str]]:
    """Rewrite literal text labels in one layout's DSL into `text_N` slots.

    Returns `(new_dsl_text, slot_names)`. Lines left untouched: non-text
    primitives, empty labels, labels already containing a slot (`{{`), and
    labels with `{`/`}` (cannot ride in the slot grammar).
    """
    out_lines: list[str] = []
    slots: list[str] = []
    for line in dsl_text.splitlines(keepends=True):
        body = line.rstrip("\n")
        m = _TEXT_LINE_RE.match(body)
        if m is None:
            out_lines.append(line)
            continue
        prefix, raw = m.group(1), m.group(2)
        if not raw or "{" in raw or "}" in raw:
            out_lines.append(line)
            continue
        name = f"text_{len(slots) + 1}"
        slots.append(name)
        default = _curlify(raw)
        new_body = f'{prefix}"{{{{ {name} | default(\\"{default}\\") }}}}"'
        out_lines.append(new_body + ("\n" if line.endswith("\n") else ""))
    return "".join(out_lines), slots


def slotify_layout_file(path: Path) -> list[str]:
    """Slotify one `.slide.dsl` in place; returns the created slot names."""
    text = path.read_text(encoding="utf-8")
    new_text, slots = slotify_dsl(text)
    if slots:
        path.write_text(new_text, encoding="utf-8")
    return slots


def _text_fit_flag(brand_pack: Path, key: str, *, default: bool = True) -> bool:
    """Read a boolean flag from ``tokens.json`` ``"text-fit"`` block.

    Supports plain bool and ``{"$value": bool}`` wrapped form.  Any parse
    error or missing file returns ``default`` (the safe non-breaking choice
    for both autoshrink and clip-to-images).
    """
    try:
        raw = json.loads((brand_pack / "tokens.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
    val = (raw.get("text-fit") or {}).get(key, default)
    if isinstance(val, dict):
        val = val.get("$value", default)
    return val if isinstance(val, bool) else str(val).lower() != "false"


def autoshrink_enabled(brand_pack: Path) -> bool:
    """Return True when the brand pack opts into autoshrink (the default).

    Pack-level opt-out: ``tokens.json`` ``"text-fit": {"autoshrink": false}``
    (or ``{"autoshrink": {"$value": false}}``).  Any parse error or missing
    file -> True (safe default).
    """
    return _text_fit_flag(brand_pack, "autoshrink", default=True)


def clip_to_images_enabled(brand_pack: Path) -> bool:
    """Return True when the brand pack opts into clip-to-images (the default).

    Pack-level opt-out: ``tokens.json`` ``"text-fit": {"clip-to-images": false}``
    (or ``{"clip-to-images": {"$value": false}}``).  Any parse error or
    missing file -> True (safe default).
    """
    return _text_fit_flag(brand_pack, "clip-to-images", default=True)


_SLOT_NAME_RE = re.compile(r"\{\{\s*(text_\d+)\b")
_TEXT_PREFIX_RE = re.compile(r'^(text\s+[^"]*?)\s*("(?:\{\{.*)$)')

# Roles whose boxes were sized for showcase copy but receive arbitrary real
# content — graceful shrink to the 10pt emit floor beats silent overflow.
_AUTOSHRINK_ROLES = frozenset({"title", "body"})


def add_autoshrink(dsl_text: str, slot_roles: dict[str, str]) -> str:
    """Add `autoshrink:true` to slot-bearing text lines whose slot role is
    title/body. Idempotent; never touches the quoted label."""
    out_lines: list[str] = []
    for line in dsl_text.splitlines(keepends=True):
        body = line.rstrip("\n")
        slot = _SLOT_NAME_RE.search(body)
        if (not body.startswith("text ") or slot is None
                or "autoshrink:" in body
                or slot_roles.get(slot.group(1)) not in _AUTOSHRINK_ROLES):
            out_lines.append(line)
            continue
        m = _TEXT_PREFIX_RE.match(body)
        if m is None:
            out_lines.append(line)
            continue
        new_body = f"{m.group(1)} autoshrink:true {m.group(2)}"
        out_lines.append(new_body + ("\n" if line.endswith("\n") else ""))
    return "".join(out_lines)
