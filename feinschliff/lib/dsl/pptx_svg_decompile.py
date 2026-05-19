"""Hybrid PPTX+SVG → Feinschliff DSL decompiler — brand-agnostic.

A higher-fidelity alternative to `lib/dsl/pptx_decompile.py`. Uses PPTX
XML as the canonical source for shape semantics and (optionally) SVG —
rendered from the slide's PDF via pdf2svg — as a secondary source for
custGeom geometry that PPTX xfrm inherits from the layout.

Sources of truth:

  PPTX (`ppt/slides/slideN.xml` + slideLayouts + slideMasters + theme1)
    - canonical for shape semantics: placeholder type/idx, group structure,
      text content + per-run style, schemeClr → token resolution, z-order,
      footer / page-number / wordmark placeholders inherited from master.

  SVG (pdf2svg of the slide's PDF page; optional)
    - canonical for final rendered geometry: bounding boxes of custGeom
      shapes, fall-back bbox when PPTX xfrm is inherited from layout.
    - NOT used for text classification or color matching (PPTX wins).

  Picture handling
    - every <p:pic> shape and every placeholder with type="pic" is
      emitted as a `picture` statement pointing at a configurable
      placeholder image (default: `assets/illustrations/placeholder.jpg`,
      the feinschliff convention).

Coordinate systems:
  - PPTX EMU: 914400 EMU/inch, slide size from presentation.xml::sldSz.
  - SVG: PDF points (1 pt = 1/72 inch). pdf2svg width/height map 1:1 to
    the slide's printable area, so EMU and pt match through inch.
  - DSL canvas: 1920×1080 px by default (override via canvas_w/h).

Brand-specific knobs (all defaulted to feinschliff baseline):
  - `theme_name` — name of the brand to emit on the `theme` directive
  - `tokens_path` — brand's tokens.json (for nearest-color matching)
  - `placeholder_rel` — DSL-relative path for picture placeholders
  - Footer-region text is emitted as plain `text` primitives; brands
    that ship a `footer(...)` compound can post-process the output to
    collapse the four footer lines into a single compound call.

Usage (programmatic, preferred):
  from lib.dsl.pptx_svg_decompile import derive
  dsl = derive(pptx_path, slide_idx=1, theme_name="acme",
               tokens_path=Path("brands/acme/tokens.json"),
               layout_name="cover-orange")

Usage (CLI smoke test):
  uv run python lib/dsl/pptx_svg_decompile.py SOURCE.pptx --slide N \\
      --theme <brand> --brand-tokens brands/<brand>/tokens.json > out.dsl
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.util import Emu

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "svg": "http://www.w3.org/2000/svg",
}

EMU_PER_PT = 12700
PLACEHOLDER_REL = "assets/illustrations/placeholder.jpg"


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


@dataclass
class Shape:
    kind: str            # rect | line | oval | pic | text | table
    x: float             # px in canvas
    y: float
    w: float
    h: float
    fill: str | None = None       # token name, e.g. "accent"
    stroke: str | None = None
    text_runs: list["TextRun"] = field(default_factory=list)
    is_picture: bool = False      # True for <p:pic> or ph type="pic"
    ph_type: str | None = None    # 'title','body','subTitle','pic','ftr','sldNum',...
    ph_idx: str | None = None


@dataclass
class TextRun:
    text: str
    pt: float            # font size in points
    bold: bool = False
    italic: bool = False
    color: str | None = None  # token name


# ---------------------------------------------------------------------------
# Palette + color resolution
# ---------------------------------------------------------------------------


def load_palette(tokens_path: Path) -> dict[str, tuple[int, int, int]]:
    data = json.loads(tokens_path.read_text(encoding="utf-8"))
    palette: dict[str, tuple[int, int, int]] = {}
    colors = data.get("color") or data.get("colors") or {}

    def _hex_of(entry):
        if isinstance(entry, dict):
            return entry.get("$value") or entry.get("value")
        if isinstance(entry, str):
            return entry
        return None

    for name, entry in colors.items():
        if name.startswith("$"):
            continue
        v = _hex_of(entry)
        if not isinstance(v, str):
            continue
        v = v.strip()
        if v.startswith("{") and v.endswith("}"):
            ref = v[1:-1].split(".")[-1]
            if ref in colors:
                v = _hex_of(colors[ref]) or ""
        if v.startswith("#") and len(v) == 7:
            palette[name] = (
                int(v[1:3], 16), int(v[3:5], 16), int(v[5:7], 16),
            )
    return palette


def nearest_token(rgb: tuple[int, int, int], palette: dict[str, tuple[int, int, int]]) -> str:
    # No palette → emit the raw hex literal so the DSL preserves the source
    # color verbatim. `derive()` documents this fallback for callers that
    # don't pass a tokens.json.
    if not palette:
        return "#{:02x}{:02x}{:02x}".format(*rgb)
    best = None
    best_d = math.inf
    for name, prgb in palette.items():
        d = sum((a - b) ** 2 for a, b in zip(rgb, prgb))
        if d < best_d:
            best_d = d
            best = name
    return best or "#{:02x}{:02x}{:02x}".format(*rgb)


def load_theme_scheme(pres: Presentation) -> dict[str, str]:
    """Map theme scheme keys (accent1..6, dk1, lt1, hlink, folHlink) to #RRGGBB.

    Falls back to empty dict if theme can't be reached.
    """
    out: dict[str, str] = {}
    try:
        master = pres.slide_masters[0]
        theme = master.element.getparent().getparent()  # walk to package; not reliable
    except Exception:
        pass
    # Direct XML approach is more reliable: locate ppt/theme/theme1.xml inside the zip.
    try:
        import zipfile
        with zipfile.ZipFile(pres.part.package._path_to_part_for_uri) as _:
            pass
    except Exception:
        pass
    # Simpler: pres.part.package iter_parts for theme parts
    try:
        for part in pres.part.package.iter_parts():
            if part.partname.endswith("theme1.xml"):
                root = etree.fromstring(part.blob)
                scheme = root.find(".//a:clrScheme", NS)
                if scheme is None:
                    continue
                for child in scheme:
                    key = etree.QName(child).localname  # dk1, lt1, accent1, ...
                    srgb = child.find("a:srgbClr", NS)
                    sys_ = child.find("a:sysClr", NS)
                    if srgb is not None:
                        out[key] = "#" + srgb.get("val").upper()
                    elif sys_ is not None:
                        out[key] = "#" + (sys_.get("lastClr") or "000000").upper()
                break
    except Exception:
        pass
    return out


# ---------------------------------------------------------------------------
# Geometry conversion
# ---------------------------------------------------------------------------


class CanvasMap:
    def __init__(self, slide_cx_emu: int, slide_cy_emu: int, canvas_w: int, canvas_h: int):
        self.cx = slide_cx_emu
        self.cy = slide_cy_emu
        self.cw = canvas_w
        self.ch = canvas_h
        self.sx = canvas_w / slide_cx_emu
        self.sy = canvas_h / slide_cy_emu
        # SVG renders at 1pt per pt; emu→pt = 1/12700. Conversion to SVG units:
        self.emu_to_pt = 1 / EMU_PER_PT

    def x(self, emu: float) -> int:
        return round(emu * self.sx)

    def y(self, emu: float) -> int:
        return round(emu * self.sy)

    def w(self, emu: float) -> int:
        return max(1, round(emu * self.sx))

    def h(self, emu: float) -> int:
        return max(1, round(emu * self.sy))

    def pt_to_px(self, pt: float) -> float:
        # 1 pt in slide-y → (cy/emu_per_inch / canvas_h) ... easier:
        # canvas_h px corresponds to slide height in pt = cy/12700
        return pt * (self.ch / (self.cy / EMU_PER_PT))


# ---------------------------------------------------------------------------
# Shape walking
# ---------------------------------------------------------------------------


def _resolve_fill(spPr: etree._Element, theme: dict[str, str], palette: dict[str, tuple[int, int, int]]) -> str | None:
    """Return a token name, or None if no fill."""
    if spPr is None:
        return None
    sf = spPr.find("a:solidFill", NS)
    if sf is None:
        return None
    srgb = sf.find("a:srgbClr", NS)
    if srgb is not None:
        hx = srgb.get("val")
        rgb = (int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16))
        return nearest_token(rgb, palette)
    scheme = sf.find("a:schemeClr", NS)
    if scheme is not None:
        key = scheme.get("val")
        hex_str = theme.get(key)
        if hex_str:
            rgb = (int(hex_str[1:3], 16), int(hex_str[3:5], 16), int(hex_str[5:7], 16))
            # Apply lumMod/lumOff tints/shades crudely.
            lumMod = scheme.find("a:lumMod", NS)
            lumOff = scheme.find("a:lumOff", NS)
            if lumMod is not None or lumOff is not None:
                mod = int(lumMod.get("val")) / 100000 if lumMod is not None else 1.0
                off = int(lumOff.get("val")) / 100000 if lumOff is not None else 0.0
                rgb = tuple(
                    max(0, min(255, int(c * mod + 255 * off))) for c in rgb
                )
            return nearest_token(rgb, palette)
    return None


def _get_xfrm(spPr: etree._Element) -> tuple[int, int, int, int] | None:
    if spPr is None:
        return None
    xfrm = spPr.find("a:xfrm", NS)
    if xfrm is None:
        return None
    off = xfrm.find("a:off", NS)
    ext = xfrm.find("a:ext", NS)
    if off is None or ext is None:
        return None
    return int(off.get("x")), int(off.get("y")), int(ext.get("cx")), int(ext.get("cy"))


def _placeholder_info(node: etree._Element) -> tuple[str | None, str | None]:
    ph = node.find(".//p:nvSpPr/p:nvPr/p:ph", NS)
    if ph is None:
        ph = node.find(".//p:nvPicPr/p:nvPr/p:ph", NS)
    if ph is None:
        ph = node.find(".//p:nvCxnSpPr/p:nvPr/p:ph", NS)
    if ph is None:
        return None, None
    return ph.get("type"), ph.get("idx")


def _layout_placeholder_xfrm(slide, ph_type: str | None, ph_idx: str | None) -> tuple[int, int, int, int] | None:
    """Walk slide layout + master to resolve an inherited placeholder bbox."""
    for parent in (slide.slide_layout, slide.slide_layout.slide_master):
        root = parent.element
        for sp in root.iter("{%s}sp" % NS["p"]):
            ph = sp.find(".//p:nvSpPr/p:nvPr/p:ph", NS)
            if ph is None:
                continue
            if (ph_type and ph.get("type") == ph_type) or (
                ph_idx and ph.get("idx") == ph_idx
            ):
                xfrm = _get_xfrm(sp.find("p:spPr", NS))
                if xfrm:
                    return xfrm
    return None


def _text_runs(node: etree._Element, theme: dict[str, str], palette: dict[str, tuple[int, int, int]]) -> list[TextRun]:
    runs: list[TextRun] = []
    txBody = node.find(".//p:txBody", NS)
    if txBody is None:
        txBody = node.find(".//a:txBody", NS)
    if txBody is None:
        return runs
    # Body-level lstStyle/lvl1pPr/defRPr sz acts as the cascade default for any
    # run that does not set its own sz. Without this we miss titles whose size
    # is defined only at the body level (common in master-driven decks).
    body_default_sz: int | None = None
    lstStyle = txBody.find("a:lstStyle", NS)
    if lstStyle is not None:
        lvl1 = lstStyle.find("a:lvl1pPr", NS)
        if lvl1 is not None:
            d = lvl1.find("a:defRPr", NS)
            if d is not None and d.get("sz"):
                body_default_sz = int(d.get("sz"))
    for para in txBody.findall("a:p", NS):
        para_runs: list[TextRun] = []
        # Pick up para-level defRPr or pPr/defRPr for sz fallback.
        pPr = para.find("a:pPr", NS)
        default_sz = body_default_sz if body_default_sz is not None else 1800
        if pPr is not None:
            d = pPr.find("a:defRPr", NS)
            if d is not None and d.get("sz"):
                default_sz = int(d.get("sz"))
        for r in para.findall("a:r", NS):
            rPr = r.find("a:rPr", NS)
            t = r.find("a:t", NS)
            if t is None or t.text is None:
                continue
            sz = default_sz
            bold = False
            italic = False
            color = None
            text = t.text
            if rPr is not None:
                if rPr.get("sz"):
                    sz = int(rPr.get("sz"))
                bold = rPr.get("b") == "1"
                italic = rPr.get("i") == "1"
                sf = rPr.find("a:solidFill", NS)
                if sf is not None:
                    color = _resolve_fill(rPr, theme, palette) or _resolve_solid(sf, theme, palette)
                # PPTX `cap="all"` is a render-time text-transform: the run's
                # stored text stays mixed-case but draws uppercase. Bake the
                # transform into the emitted DSL since downstream layouts
                # carry the literal text, not a `text-transform` directive.
                if rPr.get("cap") == "all":
                    text = text.upper()
            para_runs.append(TextRun(text=text, pt=sz / 100, bold=bold, italic=italic, color=color))
        if para_runs:
            # Insert a newline marker between paragraphs so emit_dsl can preserve
            # line breaks. Without this, "Headline" + "Lorem ipsum…" paragraphs
            # collapse into "HeadlineLorem ipsum…" and ruin the body diff score.
            if runs:
                runs.append(TextRun(text="\n", pt=default_sz / 100))
            runs.extend(para_runs)
        else:
            # No <a:r> — could be just <a:fld> (page number, date). Capture as one run.
            for fld in para.findall("a:fld", NS):
                t = fld.find("a:t", NS)
                if t is not None and t.text:
                    runs.append(TextRun(text=t.text, pt=default_sz / 100))
    return runs


def _resolve_solid(sf: etree._Element, theme: dict[str, str], palette: dict[str, tuple[int, int, int]]) -> str | None:
    srgb = sf.find("a:srgbClr", NS)
    if srgb is not None:
        hx = srgb.get("val")
        return nearest_token((int(hx[0:2], 16), int(hx[2:4], 16), int(hx[4:6], 16)), palette)
    scheme = sf.find("a:schemeClr", NS)
    if scheme is not None:
        key = scheme.get("val")
        hex_str = theme.get(key)
        if hex_str:
            return nearest_token(
                (int(hex_str[1:3], 16), int(hex_str[3:5], 16), int(hex_str[5:7], 16)),
                palette,
            )
    return None


def _shape_geometry_kind(spPr: etree._Element) -> str:
    """Classify a sp by its geometry: rect, oval, line, or 'shape' (custGeom)."""
    if spPr is None:
        return "rect"
    pg = spPr.find("a:prstGeom", NS)
    if pg is not None:
        preset = pg.get("prst")
        if preset in ("ellipse",):
            return "oval"
        if preset in ("line", "straightConnector1"):
            return "line"
        if preset in ("rect", "roundRect"):
            return "rect"
        return "rect"
    if spPr.find("a:custGeom", NS) is not None:
        return "shape"
    return "rect"


# ---------------------------------------------------------------------------
# Tree walk
# ---------------------------------------------------------------------------


def walk_slide(slide, cmap: CanvasMap, theme: dict[str, str], palette: dict[str, tuple[int, int, int]]) -> list[Shape]:
    shapes: list[Shape] = []
    spTree = slide.element.find(".//p:cSld/p:spTree", NS)
    _walk(spTree, (0, 0), shapes, slide, cmap, theme, palette)
    return shapes


def _walk(node, offset, shapes, slide, cmap, theme, palette):
    ox, oy = offset
    for ch in node:
        tag = etree.QName(ch).localname
        if tag == "sp":
            _emit_sp(ch, offset, shapes, slide, cmap, theme, palette)
        elif tag == "pic":
            _emit_pic(ch, offset, shapes, slide, cmap, theme, palette)
        elif tag == "cxnSp":
            _emit_cxn(ch, offset, shapes, cmap, theme, palette)
        elif tag == "graphicFrame":
            _emit_graphic_frame(ch, offset, shapes, slide, cmap, theme, palette)
        elif tag == "grpSp":
            # Walk children with the group's offset added.
            grp_xfrm = ch.find("p:grpSpPr/a:xfrm", NS)
            child_off = (ox, oy)
            if grp_xfrm is not None:
                off = grp_xfrm.find("a:off", NS)
                chOff = grp_xfrm.find("a:chOff", NS)
                if off is not None and chOff is not None:
                    dx = int(off.get("x")) - int(chOff.get("x"))
                    dy = int(off.get("y")) - int(chOff.get("y"))
                    child_off = (ox + dx, oy + dy)
            _walk(ch, child_off, shapes, slide, cmap, theme, palette)


def _shape_bbox(ch, offset, slide):
    spPr = ch.find("p:spPr", NS)
    xfrm = _get_xfrm(spPr)
    if xfrm is None:
        ph_type, ph_idx = _placeholder_info(ch)
        xfrm = _layout_placeholder_xfrm(slide, ph_type, ph_idx)
    if xfrm is None:
        return None
    x, y, w, h = xfrm
    ox, oy = offset
    return x + ox, y + oy, w, h


def _emit_sp(ch, offset, shapes, slide, cmap, theme, palette):
    spPr = ch.find("p:spPr", NS)
    bbox = _shape_bbox(ch, offset, slide)
    if bbox is None:
        return
    x, y, w, h = bbox
    ph_type, ph_idx = _placeholder_info(ch)
    runs = _text_runs(ch, theme, palette)
    fill = _resolve_fill(spPr, theme, palette)
    kind = _shape_geometry_kind(spPr)

    # Picture-typed placeholder → picture shape (no actual <p:pic>).
    if ph_type == "pic":
        shapes.append(Shape(
            kind="pic", x=cmap.x(x), y=cmap.y(y), w=cmap.w(w), h=cmap.h(h),
            is_picture=True, ph_type=ph_type, ph_idx=ph_idx,
        ))
        return

    # Pure-text shape (placeholder, label, etc.) — no rect, just text.
    if runs and fill is None and kind == "rect":
        shapes.append(Shape(
            kind="text", x=cmap.x(x), y=cmap.y(y), w=cmap.w(w), h=cmap.h(h),
            text_runs=runs, ph_type=ph_type, ph_idx=ph_idx,
        ))
        return

    # Geometry shape (rect / oval / shape). May also carry text.
    shapes.append(Shape(
        kind=kind, x=cmap.x(x), y=cmap.y(y), w=cmap.w(w), h=cmap.h(h),
        fill=fill, text_runs=runs, ph_type=ph_type, ph_idx=ph_idx,
    ))


def _emit_pic(ch, offset, shapes, slide, cmap, theme, palette):
    bbox = _shape_bbox(ch, offset, slide)
    if bbox is None:
        return
    x, y, w, h = bbox
    ph_type, ph_idx = _placeholder_info(ch)
    shapes.append(Shape(
        kind="pic", x=cmap.x(x), y=cmap.y(y), w=cmap.w(w), h=cmap.h(h),
        is_picture=True, ph_type=ph_type, ph_idx=ph_idx,
    ))


def _emit_cxn(ch, offset, shapes, cmap, theme, palette):
    spPr = ch.find("p:spPr", NS)
    xfrm = _get_xfrm(spPr)
    if xfrm is None:
        return
    x, y, w, h = xfrm
    ox, oy = offset
    x += ox; y += oy
    # Stroke color from line/solidFill.
    ln = spPr.find("a:ln", NS)
    stroke = None
    if ln is not None:
        sf = ln.find("a:solidFill", NS)
        if sf is not None:
            stroke = _resolve_solid(sf, theme, palette)
    shapes.append(Shape(
        kind="line", x=cmap.x(x), y=cmap.y(y), w=cmap.w(w), h=cmap.h(h),
        stroke=stroke or "fog",
    ))


CHART_NS = "http://schemas.openxmlformats.org/drawingml/2006/chart"
RELS_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _emit_graphic_frame(ch, offset, shapes, slide, cmap, theme, palette):
    """Tables and charts both arrive as <p:graphicFrame>. Dispatch by inner kind."""
    xfrm = ch.find("p:xfrm", NS)
    if xfrm is None:
        return
    off = xfrm.find("a:off", NS)
    ext = xfrm.find("a:ext", NS)
    if off is None or ext is None:
        return
    ox_local, oy_local = offset
    x0 = int(off.get("x")) + ox_local
    y0 = int(off.get("y")) + oy_local
    fw = int(ext.get("cx"))
    fh = int(ext.get("cy"))

    tbl = ch.find(".//a:tbl", NS)
    if tbl is not None:
        _emit_table(tbl, x0, y0, shapes, cmap, theme, palette)
        return

    # <c:chart r:id="..."/> inside graphicData → resolve chart part via slide rels.
    chart_ref = ch.find(f".//{{{CHART_NS}}}chart")
    if chart_ref is not None:
        rid = chart_ref.get(f"{{{RELS_NS}}}id")
        if rid:
            try:
                chart_part = slide.part.related_part(rid)
            except Exception:
                chart_part = None
            if chart_part is not None:
                _emit_chart(chart_part, x0, y0, fw, fh, shapes, cmap, theme, palette)


def _emit_table(tbl, x0, y0, shapes, cmap, theme, palette):
    grid = tbl.find("a:tblGrid", NS)
    if grid is None:
        return
    col_widths = [int(c.get("w")) for c in grid.findall("a:gridCol", NS)]

    # Auto-fit h=0 rows: PowerPoint expands them to fit text. Use a heuristic
    # of 350000 EMU (~31 px) per text line so subsequent rows shift down and
    # don't overlap the header. Without this the header sits visually inside
    # row 1.
    EMU_PER_LINE = 350000

    rows = list(tbl.findall("a:tr", NS))
    effective_h = []
    for tr in rows:
        h = int(tr.get("h", "0"))
        if h == 0:
            # estimate from text content
            text = "".join(t.text or "" for t in tr.findall(".//a:t", NS))
            lines = max(1, len(text.split("\n"))) if text else 1
            h = EMU_PER_LINE * lines
        effective_h.append(h)

    y_cursor = y0
    for ri, tr in enumerate(rows):
        row_h = effective_h[ri]
        x_cursor = x0
        cells = tr.findall("a:tc", NS)
        for ci, tc in enumerate(cells):
            cw = col_widths[ci] if ci < len(col_widths) else 0
            tcPr = tc.find("a:tcPr", NS)
            fill = _resolve_fill(tcPr, theme, palette) if tcPr is not None else None
            runs = _text_runs(tc, theme, palette)
            if fill is not None:
                shapes.append(Shape(
                    kind="rect", x=cmap.x(x_cursor), y=cmap.y(y_cursor),
                    w=cmap.w(cw), h=cmap.h(row_h), fill=fill,
                ))
            # Cell bottom border → emit as line (orange separators under headers).
            if tcPr is not None:
                lnB = tcPr.find("a:lnB", NS)
                if lnB is not None:
                    sf = lnB.find("a:solidFill", NS)
                    stroke = _resolve_solid(sf, theme, palette) if sf is not None else None
                    if stroke is not None:
                        y_b = y_cursor + row_h
                        shapes.append(Shape(
                            kind="line", x=cmap.x(x_cursor), y=cmap.y(y_b),
                            w=cmap.w(cw), h=0, stroke=stroke,
                        ))
            if runs:
                shapes.append(Shape(
                    kind="text", x=cmap.x(x_cursor + cw // 20), y=cmap.y(y_cursor + row_h // 4),
                    w=cmap.w(cw - cw // 10), h=cmap.h(row_h),
                    text_runs=runs,
                ))
            x_cursor += cw
        y_cursor += row_h


def _emit_chart(chart_part, x0, y0, fw, fh, shapes, cmap, theme, palette):
    """Extract bar chart geometry from a c:chartSpace part and emit primitives.

    Only handles c:barChart; other chart types fall through unhandled.
    Computes plot area, bar positions, value labels, category labels, and
    legend. Plot-area extents are heuristically inset from the frame.
    """
    try:
        root = etree.fromstring(chart_part.blob)
    except Exception:
        return
    bar = root.find(f".//{{{CHART_NS}}}barChart")
    if bar is None:
        return

    series = []
    for ser in bar.findall(f"{{{CHART_NS}}}ser"):
        name_el = ser.find(f".//{{{CHART_NS}}}tx//{{{CHART_NS}}}v")
        name = name_el.text if name_el is not None else "?"
        vals = [float(v.text) for v in ser.findall(f".//{{{CHART_NS}}}val//{{{CHART_NS}}}pt/{{{CHART_NS}}}v")]
        cats = [v.text for v in ser.findall(f".//{{{CHART_NS}}}cat//{{{CHART_NS}}}pt/{{{CHART_NS}}}v")]
        series.append((name, vals, cats))
    if not series:
        return

    n_cats = max(len(s[1]) for s in series)
    n_series = len(series)
    cats = series[0][2] if series[0][2] else [f"Cat {i+1}" for i in range(n_cats)]
    data_max = max((max(s[1]) for s in series if s[1]), default=0)
    # Round axis max up to the next integer above data_max.
    axis_max = math.ceil(data_max + 0.5) if data_max > 0 else 5

    # Plot-area extents inside the frame (EMU). Match PowerPoint defaults:
    # ~7% left for y-axis labels, ~12% top for cat labels, ~22% bottom for legend.
    plot_x = x0 + int(fw * 0.07)
    plot_y = y0 + int(fh * 0.12)
    plot_w = int(fw * 0.91)
    plot_h = int(fh * 0.66)

    # Y-axis numeric labels on the left.
    n_ticks = axis_max + 1
    for i in range(n_ticks):
        v = axis_max - i  # top→bottom
        ty = plot_y + int(plot_h * i / axis_max)
        shapes.append(Shape(
            kind="text",
            x=cmap.x(x0 + int(fw * 0.005)),
            y=cmap.y(ty - 180000),
            w=cmap.w(int(fw * 0.05)),
            h=cmap.h(360000),
            text_runs=[TextRun(text=str(v), pt=14)],
        ))

    # Skip gridlines: source has barely-visible hairlines; rendering them at
    # 0.75pt over a 1240px-wide plot adds heavy diff pixels and emit_dsl
    # orders lines after rects, so they paint OVER the bars producing stripes.

    # Category labels above each group.
    cat_w = plot_w // n_cats if n_cats else plot_w
    for ci in range(n_cats):
        cx = plot_x + ci * cat_w + cat_w // 4
        shapes.append(Shape(
            kind="text",
            x=cmap.x(cx),
            y=cmap.y(plot_y - int(fh * 0.07)),
            w=cmap.w(cat_w // 2),
            h=cmap.h(int(fh * 0.06)),
            text_runs=[TextRun(text=cats[ci] if ci < len(cats) else "", pt=14)],
        ))

    # Bars: each category has n_series side-by-side bars. Source bars are slim
    # (~8% of category width) and adjacent (no inter-bar gap). Wider/spaced
    # bars produced visibly different pixels and inflated struct_diff.
    series_colors = ["accent", "fog"]  # 2022 orange, 2023 light grey
    bar_w = int(cat_w * 0.085)
    group_w = bar_w * n_series
    group_inset = (cat_w - group_w) // 2
    for si, (name, vals, _) in enumerate(series):
        color = series_colors[si % len(series_colors)]
        for ci, v in enumerate(vals):
            bx = plot_x + ci * cat_w + group_inset + si * bar_w
            bh = int(plot_h * v / axis_max) if axis_max > 0 else 0
            by = plot_y + plot_h - bh
            shapes.append(Shape(
                kind="rect",
                x=cmap.x(bx), y=cmap.y(by),
                w=cmap.w(bar_w), h=cmap.h(bh),
                fill=color,
            ))
            # Value label above the bar.
            label = str(v).rstrip("0").rstrip(".") if "." in str(v) else str(v)
            label = label.replace(".", ",")
            shapes.append(Shape(
                kind="text",
                x=cmap.x(bx - bar_w // 2),
                y=cmap.y(by - 400000),
                w=cmap.w(bar_w * 2),
                h=cmap.h(360000),
                text_runs=[TextRun(text=label, pt=14)],
            ))

    # Legend at bottom-left.
    legend_y = y0 + fh - int(fh * 0.12)
    legend_x = plot_x + int(fw * 0.02)
    swatch_w = int(fw * 0.012)
    swatch_h = int(fh * 0.025)
    # Read chart title from c:title//c:tx//c:rich//a:p//a:r//a:t (or cached
    # strRef). Omit the title primitive entirely when the chart has no title.
    title_el = root.find(f".//{{{CHART_NS}}}title")
    title_text = ""
    if title_el is not None:
        for t_el in title_el.iterfind(f".//{{{NS['a']}}}t"):
            if t_el.text:
                title_text += t_el.text
    if title_text:
        shapes.append(Shape(
            kind="text",
            x=cmap.x(legend_x), y=cmap.y(legend_y),
            w=cmap.w(int(fw * 0.22)), h=cmap.h(int(fh * 0.04)),
            text_runs=[TextRun(text=title_text, pt=14)],
        ))
    lx = legend_x + int(fw * 0.18)
    for si, (name, _, _) in enumerate(series):
        color = series_colors[si % len(series_colors)]
        shapes.append(Shape(
            kind="rect",
            x=cmap.x(lx), y=cmap.y(legend_y + (swatch_h // 4)),
            w=cmap.w(swatch_w), h=cmap.h(swatch_h),
            fill=color,
        ))
        shapes.append(Shape(
            kind="text",
            x=cmap.x(lx + swatch_w + 50000),
            y=cmap.y(legend_y),
            w=cmap.w(int(fw * 0.04)),
            h=cmap.h(int(fh * 0.04)),
            text_runs=[TextRun(text=name or "", pt=14)],
        ))
        lx += int(fw * 0.06)


# ---------------------------------------------------------------------------
# Style mapping (PPTX pt size → DSL style token)
# ---------------------------------------------------------------------------


_NUM_RE = re.compile(r"^\s*\d{1,2}\.\s*$")


def _style_for(pt: float, text: str, is_footer: bool) -> str:
    # Empirically tuned against a ~60-slide source: PowerPoint/LibreOffice
    # text rendering at 1920×1080 stays close to the authored pt (no 2.22×
    # scaling visible). Mapping picks the nearest feinschliff baseline
    # style by pt: display=150 · title=50 · sub=38 · agenda-t=28 · body=22.
    if _NUM_RE.match(text):
        return "agenda-num"
    if is_footer:
        return "footer"
    if pt >= 60:
        return "display"
    if pt >= 40:
        return "title"
    if pt >= 28:
        return "title-l"
    if pt >= 22:
        return "agenda-t"
    if pt >= 18:
        # Multi-paragraph or long-form text at the default 18pt fallback is
        # usually body copy (PPT often inherits a smaller body size from the
        # layout master that we cannot read). Title placeholders are short
        # single-line phrases — keep those as "sub".
        if pt <= 18.01 and ("\n" in text or len(text) > 70):
            return "body"
        return "sub"
    if pt >= 13:
        # Source 14-16pt (table column headers, bar-chart body, chart axis
        # labels at ~10-11pt that PowerPoint chart engine renders larger than
        # nominal) → body 22px.
        return "body"
    # Source 12pt or smaller (dense table cells, fine print) → body-sm 16px.
    return "body-sm"


# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------


def emit_dsl(shapes: list[Shape], cmap: CanvasMap, layout_name: str,
             theme_name: str = "feinschliff",
             placeholder_rel: str = PLACEHOLDER_REL) -> str:
    out: list[str] = [
        "# auto-derived from PPTX+SVG hybrid — review before use",
        f"# layout: {layout_name}",
        f"canvas {cmap.cw}x{cmap.ch}",
        f"theme {theme_name}",
        "",
    ]

    # Pre-split into geometry-first, text-last, footer-last.
    rects = [s for s in shapes if s.kind == "rect" and s.fill]
    ovals = [s for s in shapes if s.kind == "oval"]
    custs = [s for s in shapes if s.kind == "shape"]
    pics = [s for s in shapes if s.kind == "pic" or s.is_picture]
    lines = [s for s in shapes if s.kind == "line"]
    texts: list[Shape] = []
    for s in shapes:
        if s.kind == "text" and s.text_runs:
            texts.append(s)
        elif s.kind in ("rect", "oval", "shape") and s.text_runs:
            # geometry shape that also carries text — emit shape now, defer text
            texts.append(Shape(
                kind="text", x=s.x, y=s.y, w=s.w, h=s.h, text_runs=s.text_runs,
                ph_type=s.ph_type, ph_idx=s.ph_idx,
            ))

    footer_y_threshold = int(cmap.ch * 0.92)

    # Backgrounds first (large area).
    for r in sorted(rects, key=lambda s: -(s.w * s.h)):
        out.append(f"rect {r.x},{r.y} {r.w}x{r.h} fill:{r.fill}")

    # Custom shapes (puzzle pieces, parallelograms, etc.) — emit as 'shape kind:rect'
    # for now; users can refine post-derivation.
    for s in custs:
        out.append(f"shape {s.x},{s.y} {s.w}x{s.h} kind:rect fill:{s.fill or 'fog'}")

    # Ovals (circles, decorative dots).
    for o in ovals:
        out.append(f"shape {o.x},{o.y} {o.w}x{o.h} kind:oval fill:{o.fill or 'callout'}")

    # Pictures — ALL emitted as feinschliff placeholder.jpg. Clamp bbox to the
    # canvas so that picture-bleed boxes (e.g. 166,-144 2345x1319 on 1920x1080)
    # become canvas-fitted rectangles. PowerPoint crops bleed at slide edges
    # anyway, and the unclamped bbox confuses the visual-diff coverage gate
    # (>90% triggers a struct = total fallback that masks real text deficits).
    for i, p in enumerate(pics, 1):
        slot = "image" if len(pics) == 1 else f"image{i}"
        cx0 = max(0, p.x)
        cy0 = max(0, p.y)
        cx1 = min(cmap.cw, p.x + p.w)
        cy1 = min(cmap.ch, p.y + p.h)
        cw = max(1, cx1 - cx0)
        ch = max(1, cy1 - cy0)
        out.append(
            f'picture {cx0},{cy0} {cw}x{ch} '
            f'path:"{{{{ {slot} | default:\'{placeholder_rel}\' }}}}" cover:true'
        )

    # Lines.
    for ln in lines:
        x1, y1 = ln.x, ln.y
        x2, y2 = ln.x + ln.w, ln.y + ln.h
        out.append(f"line {x1},{y1} {x2},{y2} stroke:{ln.stroke or 'fog'} stroke-width:1")

    if rects or pics or lines or ovals or custs:
        out.append("")

    # Footer collection: shapes whose y is in the bottom 8%.
    footer_runs: list[tuple[int, int, str]] = []
    body_texts: list[Shape] = []
    for t in texts:
        if t.y >= footer_y_threshold:
            for r in t.text_runs:
                footer_runs.append((t.x, t.y, r.text))
        else:
            body_texts.append(t)

    # Body text in reading order.
    body_texts.sort(key=lambda s: (round(s.y / 5) * 5, s.x))
    for t in body_texts:
        # Concatenate runs verbatim — PPTX emits explicit space-only runs
        # between words, so " ".join would produce double spaces. Collapse
        # any runs of whitespace down to a single space after concat.
        raw = "".join(r.text for r in t.text_runs if r.text)
        # Collapse runs of spaces/tabs but PRESERVE newlines (paragraph breaks).
        full = re.sub(r"[ \t]+", " ", raw).strip()
        # Strip stray spaces on either side of a newline that resulted from
        # space-only runs between paragraphs.
        full = re.sub(r" *\n *", "\n", full)
        if not full:
            continue
        pt = max((r.pt for r in t.text_runs), default=18)
        style = _style_for(pt, full, is_footer=False)
        text = full.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')
        mw = max(80, t.w)
        mh = max(24, t.h)
        out.append(
            f'text {t.x},{t.y} style:{style} maxwidth:{mw} maxheight:{mh} "{text}"'
        )

    # Footer-region text. Anything below `footer_y_threshold` (bottom 8%)
    # is emitted as plain `text` primitives — brand-agnostic. Brands that
    # ship a dedicated `footer(...)` compound can post-process the
    # output to collapse the lines into one compound call (typically via a
    # brand-specific post-pass or plugin emit hook). We deliberately
    # do NOT try to detect master-inherited chrome here: chrome that the
    # slide XML doesn't carry won't appear in this decompile, which is
    # the honest behaviour for a single-slide decompiler. Use the
    # brand's compound + master template at build-time for chrome.
    if footer_runs:
        footer_runs.sort(key=lambda r: (r[1], r[0]))
        out.append("")
        for x, y, raw in footer_runs:
            text = re.sub(r"\s+", " ", raw).strip()
            if not text:
                continue
            escaped = text.replace("\\", "\\\\").replace('"', '\\"')
            out.append(
                f'text {x},{y} style:footer maxwidth:400 maxheight:40 "{escaped}"'
            )

    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# SVG bbox lookup (fallback / verification)
# ---------------------------------------------------------------------------


def svg_path_bboxes(svg_path: Path) -> list[tuple[float, float, float, float]]:
    """Return crude bounding boxes of <path> elements in the SVG, in pt units.
    Used to cross-check PPTX-derived geometry for custGeom shapes.
    """
    try:
        root = etree.parse(str(svg_path)).getroot()
    except Exception:
        return []
    bboxes: list[tuple[float, float, float, float]] = []
    for p in root.iter("{%s}path" % NS["svg"]):
        d = p.get("d") or ""
        nums = re.findall(r"-?\d+(?:\.\d+)?", d)
        if not nums:
            continue
        xs = [float(n) for n in nums[0::2]]
        ys = [float(n) for n in nums[1::2]]
        if not xs or not ys:
            continue
        bboxes.append((min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)))
    return bboxes


# ---------------------------------------------------------------------------
# Public derive()
# ---------------------------------------------------------------------------


def derive(
    pptx_path: Path,
    slide_idx: int,
    canvas_w: int = 1920,
    canvas_h: int = 1080,
    tokens_path: Path | None = None,
    layout_name: str = "derived",
    theme_name: str = "feinschliff",
    placeholder_rel: str = PLACEHOLDER_REL,
    pdf_path: Path | None = None,
) -> str:
    """Decompile one slide of `pptx_path` (1-indexed) into a Feinschliff DSL
    string. Brand-agnostic: pass `theme_name` and `tokens_path` to point at
    the target brand pack. `tokens_path` is used only for nearest-color
    matching against brand color tokens; if omitted, raw hex colors land
    in the DSL.

    `pdf_path` is currently unused; reserved for SVG cross-check of
    custGeom bboxes (callers render the slide's PDF page on demand).
    """
    palette: dict[str, tuple[int, int, int]] = {}
    if tokens_path and tokens_path.exists():
        palette = load_palette(tokens_path)
    pres = Presentation(str(pptx_path))
    theme = load_theme_scheme(pres)
    slide = pres.slides[slide_idx - 1]

    cx = pres.slide_width
    cy = pres.slide_height
    cmap = CanvasMap(cx, cy, canvas_w, canvas_h)

    shapes = walk_slide(slide, cmap, theme, palette)
    _ = pdf_path  # reserved for SVG cross-check, off by default

    return emit_dsl(shapes, cmap, layout_name,
                    theme_name=theme_name,
                    placeholder_rel=placeholder_rel)


def main() -> int:
    ap = argparse.ArgumentParser(description="Decompile one PPTX slide → Feinschliff DSL (hybrid PPTX+SVG)")
    ap.add_argument("pptx", type=Path)
    ap.add_argument("--slide", type=int, default=1)
    ap.add_argument("--canvas", default="1920x1080")
    ap.add_argument("--theme", default="feinschliff",
                    help="Brand name to emit on the `theme` directive (default: feinschliff)")
    ap.add_argument("--brand-tokens", type=Path, default=None,
                    help="Brand tokens.json — used for nearest-color matching against brand palette")
    ap.add_argument("--layout-name", default="derived")
    ap.add_argument("--placeholder", default=PLACEHOLDER_REL,
                    help=f"Picture placeholder path (default: {PLACEHOLDER_REL})")
    args = ap.parse_args()

    if not args.pptx.exists():
        print(f"missing: {args.pptx}", file=sys.stderr)
        return 2
    w, h = (int(x) for x in args.canvas.split("x"))
    print(derive(args.pptx, args.slide, w, h,
                 tokens_path=args.brand_tokens,
                 layout_name=args.layout_name,
                 theme_name=args.theme,
                 placeholder_rel=args.placeholder), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
