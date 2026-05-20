"""Structural validator for diagram artifacts.

Two layers of check, both deterministic (no vision model needed):

**A. File well-formedness** — `validate_svg_file` / `validate_excalidraw_file`.
Catches malformed JSON, missing `<svg>` tag, missing `viewBox`. Cheap; runs
before anything tries to render. (Folded in from the former
`lib/diagrams/mechanical_checks.py`.)

**B. Structural rules on Excalidraw documents** — `validate_excalidraw_structure`.
Runs after expansion, on the in-memory JSON. Catches the failure modes
that consistently break a diagram's legibility:

  - **diagram-overflow** — text bound to a container exceeds the inner box
    (Excalidraw renders text-clipping silently; this surfaces it).
  - **diagram-shape-overlap** — two non-text shapes whose bboxes overlap
    without a parent/child (nested) relationship. The "rect on top of
    rect" bug.
  - **diagram-text-collision** — two free-floating text elements whose
    bboxes overlap. The "annotations stacked on each other" bug.
  - **diagram-arrow-cross-zone-unrouted** — a two-point arrow whose
    endpoints fall inside two different zones AND whose direction is
    diagonal (both dx and dy non-zero). The "von irgendwo nach irgendwo"
    look. FATAL — author must add port anchors + route:elbow (or via:).
    See methodology §5a.
  - **diagram-arrow-crossing** — an arrow's line segment crosses a
    non-endpoint shape. Advisory (WARN) — the heuristic can false-positive
    on arrows that intentionally route around a shape.

Salvaged and consolidated 2026-05-16 from `lib/diagram/validator.py` (which
had the rich logic but was never wired into production) and
`lib/diagrams/mechanical_checks.py` (37 LOC of just-the-file-checks).
Returns structured `Defect` records keyed to `DefectKind` so callers can
integrate with the same defect taxonomy used by `cli/verify`.

Usage:

    from feinschliff_builder.diagrams.structural_validator import (
        validate_excalidraw_structure,
        validate_excalidraw_file,
        validate_svg_file,
    )

    defects = validate_excalidraw_structure(doc)
    defects += validate_excalidraw_file(path)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from feinschliff.defects import Defect, DefectKind, Severity
from feinschliff.diagrams.text_metrics import CHAR_WIDTH_EM as _CHAR_WIDTH_EM


# Font metrics approximate what Excalidraw renders at runtime. The DSL uses
# fontFamily 3 (monospace, Cascadia) at specific sizes; monospace glyphs
# average ~0.6 em wide; line-height is 1.25 per `excalidraw_expand.py`.
# _CHAR_WIDTH_EM is imported from text_metrics (single source of truth).
_LINE_HEIGHT = 1.25
# Slack to absorb sub-pixel rounding and font-substitution variance.
_OVERFLOW_TOLERANCE_PX = 6.0


@dataclass
class _Box:
    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float: return self.x + self.w
    @property
    def bottom(self) -> float: return self.y + self.h


def _box(el: dict) -> _Box:
    return _Box(el.get("x", 0), el.get("y", 0),
                el.get("width", 0), el.get("height", 0))


def _intersects(a: _Box, b: _Box, *, tolerance: float = 0.0) -> bool:
    """True if two boxes overlap by more than `tolerance` px on both axes."""
    dx = min(a.right, b.right) - max(a.x, b.x)
    dy = min(a.bottom, b.bottom) - max(a.y, b.y)
    return dx > tolerance and dy > tolerance


def _measure_text(text: str, font_size: float) -> tuple[float, float]:
    """Approximate bbox of a multi-line text string at the given size.

    Matches the math in `excalidraw_expand.py` so validator findings line
    up with what the renderer will actually produce."""
    lines = text.split("\n")
    max_line = max((len(line) for line in lines), default=0)
    width = max_line * font_size * _CHAR_WIDTH_EM
    height = font_size * _LINE_HEIGHT * len(lines)
    return width, height


# ─── Structural checks (run over expanded Excalidraw documents) ──────────


def _check_bound_text_overflow(doc: dict) -> list[Defect]:
    """Text bound to a container must fit inside the container's inner box."""
    out: list[Defect] = []
    by_id = {el.get("id"): el for el in doc.get("elements", [])}
    for el in doc.get("elements", []):
        if el.get("type") != "text":
            continue
        parent_id = el.get("containerId")
        if not parent_id or parent_id not in by_id:
            continue
        parent = by_id[parent_id]
        p_box = _box(parent)
        text = el.get("originalText") or el.get("text") or ""
        size = el.get("fontSize", 16)
        want_w, want_h = _measure_text(text, size)
        # Excalidraw reserves ~8px horizontal padding inside a container.
        slack_w, slack_h = 8, 0
        if want_w > p_box.w - slack_w + _OVERFLOW_TOLERANCE_PX:
            out.append(Defect(
                slide_index=0,
                kind=DefectKind.DIAGRAM_OVERFLOW,
                severity=Severity.FATAL,
                message=(
                    f"text {el.get('id')!r} needs width≈{want_w:.0f}px, "
                    f"container {parent_id!r} has {p_box.w:.0f}px "
                    f"(text: {text[:50]!r})"
                ),
                meta={"axis": "width", "element_id": el.get("id"),
                      "container_id": parent_id},
            ))
        if want_h > p_box.h - slack_h + _OVERFLOW_TOLERANCE_PX:
            out.append(Defect(
                slide_index=0,
                kind=DefectKind.DIAGRAM_OVERFLOW,
                severity=Severity.FATAL,
                message=(
                    f"text {el.get('id')!r} needs height≈{want_h:.0f}px, "
                    f"container {parent_id!r} has {p_box.h:.0f}px "
                    f"(text: {text[:50]!r})"
                ),
                meta={"axis": "height", "element_id": el.get("id"),
                      "container_id": parent_id},
            ))
    return out


def _check_shape_overlap(doc: dict) -> list[Defect]:
    """Non-trivial overlap between shapes that aren't parent/child."""
    out: list[Defect] = []
    shapes = [
        el for el in doc.get("elements", [])
        if el.get("type") in ("rectangle", "ellipse", "diamond")
    ]
    for i, a in enumerate(shapes):
        ba = _box(a)
        for b in shapes[i + 1:]:
            bb = _box(b)
            if not _intersects(ba, bb, tolerance=4):
                continue
            # Full containment in either direction = intended nesting
            # (decorative band + sub-card pattern). Not a defect.
            if (ba.x <= bb.x and ba.y <= bb.y
                    and ba.right >= bb.right and ba.bottom >= bb.bottom):
                continue
            if (bb.x <= ba.x and bb.y <= ba.y
                    and bb.right >= ba.right and bb.bottom >= ba.bottom):
                continue
            out.append(Defect(
                slide_index=0,
                kind=DefectKind.DIAGRAM_SHAPE_OVERLAP,
                severity=Severity.FATAL,
                message=(
                    f"{a.get('id')!r} and {b.get('id')!r} overlap without "
                    f"full containment "
                    f"(A {ba.x:.0f},{ba.y:.0f} {ba.w:.0f}×{ba.h:.0f}  "
                    f"B {bb.x:.0f},{bb.y:.0f} {bb.w:.0f}×{bb.h:.0f})"
                ),
                meta={"a_id": a.get("id"), "b_id": b.get("id")},
            ))
    return out


def _check_free_text_collision(doc: dict) -> list[Defect]:
    """Two free-floating text blocks shouldn't overlap."""
    out: list[Defect] = []
    texts = [
        el for el in doc.get("elements", [])
        if el.get("type") == "text" and not el.get("containerId")
    ]
    for i, a in enumerate(texts):
        ba = _box(a)
        for b in texts[i + 1:]:
            bb = _box(b)
            if _intersects(ba, bb, tolerance=4):
                ta = (a.get("originalText") or a.get("text") or "")[:30]
                tb = (b.get("originalText") or b.get("text") or "")[:30]
                out.append(Defect(
                    slide_index=0,
                    kind=DefectKind.DIAGRAM_TEXT_COLLISION,
                    severity=Severity.FATAL,
                    message=(
                        f"{a.get('id')!r} ({ta!r}) and "
                        f"{b.get('id')!r} ({tb!r}) overlap"
                    ),
                    meta={"a_id": a.get("id"), "b_id": b.get("id")},
                ))
    return out


def _check_arrow_cross_zone_unrouted(doc: dict) -> list[Defect]:
    """A two-point arrow whose endpoints lie inside two different zones
    AND whose direction is diagonal (both dx and dy non-zero) is the
    "von irgendwo nach irgendwo" defect: the centre-to-centre ray cuts
    across other zones and other arrows, the author skipped both ports
    and `route:elbow` / `via:`.

    The escape hatches that bypass this check are exactly the routing
    primitives we want authors to reach for: any of
      - port anchor on src or dst (forces a perpendicular exit/entry,
        often makes the segment axis-aligned),
      - `route:elbow` (emits a polyline with >2 points),
      - `via:x,y;...` waypoints (emits a polyline with >2 points)
    will produce either an axis-aligned 2-point line or a >2-point
    polyline, both of which exit this check.

    A pure horizontal or vertical 2-point arrow is allowed even across
    zones — same-row left-to-right arrows that traverse a zone boundary
    look fine.
    """
    elements = doc.get("elements", [])
    zones = [
        el for el in elements
        if el.get("type") == "rectangle"
        and (el.get("customData") or {}).get("dsl_kind") == "zone"
    ]
    if not zones:
        return []

    def _zone_at(px: float, py: float) -> str | None:
        for z in zones:
            zb = _box(z)
            if zb.x <= px <= zb.right and zb.y <= py <= zb.bottom:
                return (z.get("customData") or {}).get("dsl_id") or z.get("id")
        return None

    out: list[Defect] = []
    for el in elements:
        if el.get("type") != "arrow":
            continue
        pts = el.get("points") or []
        # Polyline with >2 points = author used elbow / via. Trust it.
        if len(pts) != 2:
            continue
        x0 = el.get("x", 0)
        y0 = el.get("y", 0)
        sx, sy = x0 + pts[0][0], y0 + pts[0][1]
        ex, ey = x0 + pts[1][0], y0 + pts[1][1]
        dx, dy = ex - sx, ey - sy
        # Axis-aligned 2-point arrow — even across zones it reads as a
        # clean L→R or top→bottom hop. Not the diagonal we're flagging.
        if abs(dx) < 1.0 or abs(dy) < 1.0:
            continue
        src_zone = _zone_at(sx, sy)
        dst_zone = _zone_at(ex, ey)
        # Free-space endpoints (no zone) or same-zone diagonals are
        # other problems (covered by _check_arrow_through_shape and by
        # the methodology doc's "use ports on same-row arrows" rule)
        # but not this defect.
        if src_zone is None or dst_zone is None or src_zone == dst_zone:
            continue
        out.append(Defect(
            slide_index=0,
            kind=DefectKind.DIAGRAM_ARROW_CROSS_ZONE_UNROUTED,
            severity=Severity.FATAL,
            message=(
                f"arrow {el.get('id')!r} is a diagonal across zones "
                f"{src_zone!r}→{dst_zone!r}. Use a port anchor "
                f"(:top/:bottom/:left/:right) on both endpoints plus "
                f"`route:elbow` (or `via:x,y;...`) and add a label. "
                f"See skills/excalidraw/references/methodology.md §5a."
            ),
            meta={
                "arrow_id": el.get("id"),
                "src_zone": src_zone,
                "dst_zone": dst_zone,
            },
        ))
    return out


def _check_arrow_through_shape(doc: dict) -> list[Defect]:
    """Arrows whose line segment crosses a non-endpoint rect are likely
    visually unreadable. Heuristic — advisory only (severity=WARN)."""
    out: list[Defect] = []
    rects = [
        el for el in doc.get("elements", [])
        if el.get("type") in ("rectangle", "ellipse", "diamond")
    ]
    for el in doc.get("elements", []):
        if el.get("type") != "arrow":
            continue
        start_id = (el.get("startBinding") or {}).get("elementId")
        end_id = (el.get("endBinding") or {}).get("elementId")
        endpoints = {start_id, end_id}
        x0 = el.get("x", 0)
        y0 = el.get("y", 0)
        pts = el.get("points", [])
        if not pts:
            continue
        ax0, ay0 = x0 + pts[0][0], y0 + pts[0][1]
        ax1, ay1 = x0 + pts[-1][0], y0 + pts[-1][1]
        arrow_box = _Box(
            min(ax0, ax1), min(ay0, ay1),
            abs(ax1 - ax0) or 1, abs(ay1 - ay0) or 1,
        )
        for r in rects:
            if r.get("id") in endpoints:
                continue
            rb = _box(r)
            # Decorative band containing the arrow is intended nesting.
            if (rb.x <= arrow_box.x and rb.y <= arrow_box.y
                    and rb.right >= arrow_box.right
                    and rb.bottom >= arrow_box.bottom):
                continue
            if _intersects(arrow_box, rb, tolerance=0):
                out.append(Defect(
                    slide_index=0,
                    kind=DefectKind.DIAGRAM_ARROW_CROSSING,
                    severity=Severity.WARN,
                    message=(
                        f"arrow {el.get('id')!r} passes through "
                        f"non-endpoint {r.get('id')!r}"
                    ),
                    meta={"arrow_id": el.get("id"), "shape_id": r.get("id")},
                ))
    return out


def validate_excalidraw_structure(doc: dict) -> list[Defect]:
    """Run every structural rule on an in-memory Excalidraw doc."""
    out: list[Defect] = []
    out += _check_bound_text_overflow(doc)
    out += _check_free_text_collision(doc)
    out += _check_shape_overlap(doc)
    out += _check_arrow_cross_zone_unrouted(doc)
    out += _check_arrow_through_shape(doc)
    return out


# ─── Structural rules on SVG output (the markup, not the DSL) ─────────────

_SVG_NS = "http://www.w3.org/2000/svg"
# Match the opening <svg ...> tag (up to its closing `>`) so the
# width/height fallback only sees the root element's attributes, not
# the width="..." on a child rect/use/etc.
_SVG_ROOT_RE = re.compile(r"<svg\b[^>]*>", re.DOTALL)
_VIEWBOX_RE = re.compile(
    r'viewBox="\s*(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+'
    r'(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)"'
)


def _svg_canvas_bounds(svg_text: str) -> _Box | None:
    """Best-effort parse of the SVG's logical canvas from viewBox.

    Falls back to width/height attributes on the root `<svg>` tag if
    viewBox is missing. Returns None when neither is parseable — caller
    can skip the bounds check."""
    root_m = _SVG_ROOT_RE.search(svg_text)
    if not root_m:
        return None
    root_tag = root_m.group(0)
    m = _VIEWBOX_RE.search(root_tag)
    if m:
        x, y, w, h = (float(g) for g in m.groups())
        return _Box(x, y, w, h)
    m_w = re.search(r'\bwidth="(\d+(?:\.\d+)?)"', root_tag)
    m_h = re.search(r'\bheight="(\d+(?:\.\d+)?)"', root_tag)
    if m_w and m_h:
        return _Box(0, 0, float(m_w.group(1)), float(m_h.group(1)))
    return None


# Element kinds with axis-aligned (x, y, width, height) attributes.
_RECT_LIKE_TAGS = ("rect", "image", "foreignObject", "use")


def _svg_positioned_elements(root) -> list[tuple[str, _Box]]:
    """Walk SVG tree, return [(tag, bbox)] for every positioned primitive
    whose bbox is computable from local attributes only.

    Elements inside a `<g transform="translate(...)">` would need full
    transform resolution; we intentionally skip them rather than
    false-positive. The motivating check (off-canvas) is most useful for
    top-level positioned shapes anyway."""
    found: list[tuple[str, _Box]] = []

    def _local_tag(el) -> str:
        tag = el.tag
        return tag.split("}", 1)[1] if "}" in tag else tag

    for el in root.iter():
        if _local_tag(el).lower() == "g":
            # Skip groups with transforms — handling them properly needs
            # full SVG matrix math. Plain ungrouped shapes inside still
            # show up via iter().
            continue
        tag = _local_tag(el).lower()
        try:
            if tag in _RECT_LIKE_TAGS:
                x = float(el.get("x", 0))
                y = float(el.get("y", 0))
                w = float(el.get("width", 0))
                h = float(el.get("height", 0))
                if w > 0 and h > 0:
                    found.append((tag, _Box(x, y, w, h)))
            elif tag == "circle":
                cx = float(el.get("cx", 0))
                cy = float(el.get("cy", 0))
                r = float(el.get("r", 0))
                if r > 0:
                    found.append((tag, _Box(cx - r, cy - r, 2 * r, 2 * r)))
            elif tag == "ellipse":
                cx = float(el.get("cx", 0))
                cy = float(el.get("cy", 0))
                rx = float(el.get("rx", 0))
                ry = float(el.get("ry", 0))
                if rx > 0 and ry > 0:
                    found.append((tag, _Box(cx - rx, cy - ry, 2 * rx, 2 * ry)))
            elif tag == "text":
                # Text bbox is hard to compute without font metrics; use a
                # zero-size point at (x, y) so we at least catch "text positioned
                # way off canvas" (the most common authoring mistake).
                x = float(el.get("x", 0))
                y = float(el.get("y", 0))
                found.append((tag, _Box(x, y, 1, 1)))
        except (TypeError, ValueError):
            # Non-numeric attribute (rare, but don't crash a build over it).
            continue
    return found


def validate_svg_structure(svg_text: str) -> list[Defect]:
    """Run every structural rule on raw SVG markup.

    Today: off-canvas detection only. The SVG DSL admits many shapes
    that can be intentionally overlapped (callouts over bars, braces
    spanning multiple primitives), so we don't run shape-overlap here.
    Off-canvas is the unambiguous authoring mistake — a primitive whose
    bbox lies partly outside the declared viewBox / width × height won't
    render where the author thinks it will."""
    try:
        from lxml import etree
        root = etree.fromstring(svg_text.encode("utf-8") if isinstance(svg_text, str) else svg_text)
    except Exception as exc:
        # Mark as invalid-file; caller decides whether to fail.
        return [Defect(
            slide_index=0, kind=DefectKind.DIAGRAM_INVALID_FILE,
            severity=Severity.FATAL,
            message=f"svg parse failed: {exc}",
            meta={},
        )]

    canvas = _svg_canvas_bounds(svg_text)
    if canvas is None:
        # Can't bounds-check what we can't measure. Caller's
        # validate_svg_file already warned about the missing viewBox.
        return []

    # 4-px tolerance: stroke widths drawn flush to the edge are common
    # and shouldn't trip the off-canvas check.
    SLACK = 4.0
    out: list[Defect] = []
    for tag, box in _svg_positioned_elements(root):
        off_left = box.x < canvas.x - SLACK
        off_top = box.y < canvas.y - SLACK
        off_right = box.right > canvas.right + SLACK
        off_bottom = box.bottom > canvas.bottom + SLACK
        if off_left or off_top or off_right or off_bottom:
            sides = []
            if off_left:
                sides.append("left")
            if off_top:
                sides.append("top")
            if off_right:
                sides.append("right")
            if off_bottom:
                sides.append("bottom")
            out.append(Defect(
                slide_index=0,
                kind=DefectKind.DIAGRAM_OVERFLOW,
                severity=Severity.FATAL,
                message=(
                    f"<{tag}> at ({box.x:.0f},{box.y:.0f}) "
                    f"{box.w:.0f}×{box.h:.0f} extends off canvas "
                    f"({canvas.w:.0f}×{canvas.h:.0f}) on: {', '.join(sides)}"
                ),
                meta={"tag": tag, "sides": sides},
            ))
    return out


# ─── File well-formedness (folded in from mechanical_checks) ──────────────


def validate_svg_file(path: Path) -> list[Defect]:
    """Cheap checks on an .svg file before it's handed to a renderer."""
    text = path.read_text()
    out: list[Defect] = []
    if "<svg" not in text:
        out.append(Defect(
            slide_index=0, kind=DefectKind.DIAGRAM_INVALID_FILE,
            severity=Severity.FATAL,
            message=f"{path.name}: not an SVG document (no <svg> tag)",
            meta={"path": str(path)},
        ))
        return out
    if "viewBox=" not in text:
        out.append(Defect(
            slide_index=0, kind=DefectKind.DIAGRAM_INVALID_FILE,
            severity=Severity.WARN,
            message=f"{path.name}: svg missing viewBox (renderers will guess)",
            meta={"path": str(path)},
        ))
    if not re.search(r"(width|height)=", text):
        out.append(Defect(
            slide_index=0, kind=DefectKind.DIAGRAM_INVALID_FILE,
            severity=Severity.WARN,
            message=f"{path.name}: svg missing width/height (rasterizers will guess)",
            meta={"path": str(path)},
        ))
    return out


def validate_excalidraw_file(path: Path) -> list[Defect]:
    """Cheap checks on an .excalidraw file before it's handed to a renderer."""
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [Defect(
            slide_index=0, kind=DefectKind.DIAGRAM_INVALID_FILE,
            severity=Severity.FATAL,
            message=f"{path.name}: invalid JSON: {e}",
            meta={"path": str(path)},
        )]
    out: list[Defect] = []
    if data.get("type") != "excalidraw":
        out.append(Defect(
            slide_index=0, kind=DefectKind.DIAGRAM_INVALID_FILE,
            severity=Severity.FATAL,
            message=f"{path.name}: missing or wrong 'type' field",
            meta={"path": str(path)},
        ))
    if "elements" not in data:
        out.append(Defect(
            slide_index=0, kind=DefectKind.DIAGRAM_INVALID_FILE,
            severity=Severity.FATAL,
            message=f"{path.name}: missing 'elements' array",
            meta={"path": str(path)},
        ))
    if "appState" not in data:
        out.append(Defect(
            slide_index=0, kind=DefectKind.DIAGRAM_INVALID_FILE,
            severity=Severity.WARN,
            message=f"{path.name}: missing 'appState'",
            meta={"path": str(path)},
        ))
    return out


def validate_diagram_file(path: Path) -> list[Defect]:
    """Dispatch by extension: well-formedness + structural rules."""
    ext = path.suffix.lower()
    if ext == ".svg":
        defects = validate_svg_file(path)
        if any(d.severity == Severity.FATAL for d in defects):
            return defects
        defects += validate_svg_structure(path.read_text())
        return defects
    if ext == ".excalidraw":
        defects = validate_excalidraw_file(path)
        # Fatal file-level problems mean we can't trust the JSON for
        # structural checks — bail early.
        if any(d.severity == Severity.FATAL for d in defects):
            return defects
        try:
            doc = json.loads(path.read_text())
        except json.JSONDecodeError:
            return defects
        defects += validate_excalidraw_structure(doc)
        return defects
    raise ValueError(f"validate_diagram_file: unsupported extension {ext!r}")
