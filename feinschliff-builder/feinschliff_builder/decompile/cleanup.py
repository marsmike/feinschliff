"""Post-decompile cleanup passes over a freshly derived `.slide.dsl`.

Flattening slideLayout/slideMaster inheritance (scripts/pptx_flatten_inherited.py)
makes master-based templates decompilable but brings template noise that the
hybrid decompiler currently reproduces faithfully:

  1. some flattened texts emit twice (exact-duplicate `text` lines);
  2. layout-placeholder prompt copies double a slide's own prompt box
     (two text boxes with near-identical rects, IoU > ~0.97);
  3. picture-frame helper captions ("Add Picture", "Add Text\\n…") land as
     real text boxes that overlay photos and shift slot numbering;
  4. the layout-placeholder *picture* is carried on top of the slide's own
     picture (two stacked near-identical native pics).

These passes run per slide right after `derive()` (see
scripts/brand_decompile_all.py). All are idempotent. Keep-later policy on
the overlap passes: the decompiler emits in z-order, slide-owned shapes
last, so the LATER of two near-identical boxes is the slide's own.
"""
from __future__ import annotations

import base64
import re

__all__ = [
    "dedupe_text_lines",
    "drop_prompt_copies",
    "drop_helper_captions",
    "dedupe_native_pics",
    "cleanup_dsl",
    "unslotified_text_report",
]

_TEXT_GEO_RE = re.compile(
    r"^text\s+(\d+),(\d+)\b.*?maxwidth:(\d+)\s+maxheight:(\d+)")
_TEXT_LABEL_RE = re.compile(r'^text\s+\d+,\d+\b.*"(.*)"\s*$')
_NATIVE_B64_RE = re.compile(r'^native\s+\w+\s.*?b64:"([^"]+)"')
_XFRM_OFF_RE = re.compile(r'<a:off x="(-?\d+)" y="(-?\d+)"/>')
_XFRM_EXT_RE = re.compile(r'<a:ext cx="(\d+)" cy="(\d+)"/>')
_BAKED_T_RE = re.compile(r"<a:t>([^<]+)</a:t>")

# Helper captions PowerPoint bakes into picture/content frames. Exact match
# for the picture helper; prefix match for the multi-level text helper.
HELPER_CAPTION_EXACT = ("Add Picture",)
HELPER_CAPTION_PREFIX = ("Add Text\\n",)

# Near-identical rects only: true prompt copies overlap at >= ~0.97; real
# label/value pairs in KPI tiles overlap around 0.4-0.75 and must survive.
PROMPT_COPY_IOU = 0.9


def _iou(a: tuple, b: tuple) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0.0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0.0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    union = aw * ah + bw * bh - inter
    return inter / union if union else 0.0


def dedupe_text_lines(dsl_text: str) -> tuple[str, int]:
    """Drop exact-duplicate `text` lines (keep the first occurrence)."""
    out, seen, dropped = [], set(), 0
    for line in dsl_text.splitlines(keepends=True):
        body = line.rstrip("\n")
        if body.startswith("text ") and body in seen:
            dropped += 1
            continue
        if body.startswith("text "):
            seen.add(body)
        out.append(line)
    return "".join(out), dropped


def drop_prompt_copies(dsl_text: str, *, iou: float = PROMPT_COPY_IOU
                       ) -> tuple[str, int]:
    """Drop the earlier of two text boxes whose rects are near-identical."""
    lines = dsl_text.splitlines(keepends=True)
    boxes = []
    for i, line in enumerate(lines):
        m = _TEXT_GEO_RE.match(line.strip())
        if m:
            boxes.append((i, tuple(float(g) for g in m.groups())))
    drop: set[int] = set()
    for a in range(len(boxes)):
        for b in range(a + 1, len(boxes)):
            ia, ra = boxes[a]
            ib, rb = boxes[b]
            if ia not in drop and _iou(ra, rb) > iou:
                drop.add(ia)
    return ("".join(ln for i, ln in enumerate(lines) if i not in drop),
            len(drop))


def drop_helper_captions(dsl_text: str) -> tuple[str, int]:
    """Drop PowerPoint's picture/content-frame helper captions."""
    out, dropped = [], 0
    for line in dsl_text.splitlines(keepends=True):
        m = _TEXT_LABEL_RE.match(line.strip())
        if m:
            label = m.group(1)
            if label in HELPER_CAPTION_EXACT or any(
                    label.startswith(p) for p in HELPER_CAPTION_PREFIX):
                dropped += 1
                continue
        out.append(line)
    return "".join(out), dropped


def _native_rect_emu(line: str) -> tuple | None:
    m = _NATIVE_B64_RE.match(line.strip())
    if m is None:
        return None
    try:
        xml = base64.b64decode(m.group(1)).decode("utf-8", "replace")
    except ValueError:
        return None
    off, ext = _XFRM_OFF_RE.search(xml), _XFRM_EXT_RE.search(xml)
    if not (off and ext):
        return None
    return (float(off.group(1)), float(off.group(2)),
            float(ext.group(1)), float(ext.group(2)))


def dedupe_native_pics(dsl_text: str, *, iou: float = PROMPT_COPY_IOU
                       ) -> tuple[str, int]:
    """Drop the earlier of two native pics with near-identical rects (EMU —
    IoU is scale-invariant, so no canvas conversion is needed)."""
    lines = dsl_text.splitlines(keepends=True)
    rects = []
    for i, line in enumerate(lines):
        if not line.strip().startswith("native "):
            continue
        r = _native_rect_emu(line)
        if r is not None:
            rects.append((i, r))
    drop: set[int] = set()
    for a in range(len(rects)):
        for b in range(a + 1, len(rects)):
            ia, ra = rects[a]
            ib, rb = rects[b]
            if ia not in drop and _iou(ra, rb) > iou:
                drop.add(ia)
    return ("".join(ln for i, ln in enumerate(lines) if i not in drop),
            len(drop))


def cleanup_dsl(dsl_text: str) -> tuple[str, dict[str, int]]:
    """Run all post-decompile cleanup passes; returns (new_dsl, stats)."""
    stats: dict[str, int] = {}
    dsl_text, stats["dedupe_text"] = dedupe_text_lines(dsl_text)
    dsl_text, stats["prompt_copies"] = drop_prompt_copies(dsl_text)
    dsl_text, stats["helper_captions"] = drop_helper_captions(dsl_text)
    dsl_text, stats["native_pic_dupes"] = dedupe_native_pics(dsl_text)
    return dsl_text, stats


_CHART_MARKERS = ("<c:chart", "<dgm:", "relIds")


def unslotified_text_report(dsl_text: str, asset_root=None) -> list[str]:
    """Texts a deck author cannot bind: literal `text` labels that escaped
    slotification, plus literal `<a:t>` runs in non-chart native payloads.

    The per-slide decompile loop runs slotify until this report is empty
    (chart/SmartArt labels excepted — those live in external parts)."""
    leftovers: list[str] = []
    for line in dsl_text.splitlines():
        body = line.strip()
        m = _TEXT_LABEL_RE.match(body)
        if m and m.group(1) and "{{" not in m.group(1):
            leftovers.append(f"text literal: {m.group(1)[:60]!r}")
            continue
        if not body.startswith("native "):
            continue
        xml = None
        bm = _NATIVE_B64_RE.match(body)
        if bm:
            try:
                xml = base64.b64decode(bm.group(1)).decode("utf-8", "replace")
            except ValueError:
                xml = None
        elif asset_root is not None:
            fm = re.search(r'xml_file:"([^"]+)"', body)
            if fm and (asset_root / fm.group(1)).is_file():
                xml = (asset_root / fm.group(1)).read_text(
                    encoding="utf-8", errors="replace")
        if xml is None or any(s in xml for s in _CHART_MARKERS):
            continue
        for t in _BAKED_T_RE.findall(xml):
            if t.strip() and "{{" not in t:
                leftovers.append(f"native text run: {t[:60]!r}")
    return leftovers
