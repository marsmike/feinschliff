"""Pre-render layout validation: detect overlapping text and out-of-bounds shapes.

Runs after each slide is built but before the deck is saved. Cheap (one
shape-tree walk per slide) and catches the largest class of defects the
verify-PNG-eyeball step otherwise has to flag manually — title spilling onto
content cards, content card spilling off the canvas, etc.

The validator only checks *text* shapes against each other. Background
rectangles and chrome (hairlines, accent strips) routinely sit underneath
text and would produce constant false positives — those are skipped.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class LayoutDefect:
    kind: str               # "text-overlap" | "out-of-bounds"
    slide_index: int        # 1-based
    shape_a: str            # text snippet or label
    shape_b: str | None
    message: str

    def __str__(self) -> str:
        return f"slide {self.slide_index} [{self.kind}] {self.message}"


def _bbox(shape) -> tuple[int, int, int, int]:
    """Axis-aligned bounding box, accounting for shape rotation.

    python-pptx exposes left/top/width/height as the pre-rotation rect.
    For rotated shapes (e.g. a -90° axis label), the visible footprint is
    a different rectangle pivoted on the bbox center. We project the four
    rotated corners back to an AABB so overlap checks reflect what the
    eye actually sees.
    """
    left, top, w, h = shape.left, shape.top, shape.width, shape.height
    rot = float(getattr(shape, "rotation", 0.0) or 0.0)
    if rot % 360 == 0:
        return (left, top, left + w, top + h)
    import math
    cx, cy = left + w / 2.0, top + h / 2.0
    theta = math.radians(rot)
    cos_t, sin_t = math.cos(theta), math.sin(theta)
    corners = [(-w / 2, -h / 2), (w / 2, -h / 2),
               (w / 2,  h / 2), (-w / 2,  h / 2)]
    xs, ys = [], []
    for dx, dy in corners:
        xs.append(cx + dx * cos_t - dy * sin_t)
        ys.append(cy + dx * sin_t + dy * cos_t)
    return (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))


def _overlaps(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return not (ax2 <= bx1 or bx2 <= ax1 or ay2 <= by1 or by2 <= ay1)


def _text_snippet(shape, n: int = 40) -> str:
    if not shape.has_text_frame:
        return "(no text)"
    t = shape.text_frame.text.split("\n")[0].strip()
    return (t[:n] + "…") if len(t) > n else t or "(empty)"


def validate_slide(
    slide,
    *,
    slide_index: int,
    slide_w: int,
    slide_h: int,
) -> list[LayoutDefect]:
    """Walk all shapes; emit overlap warnings between *text* shapes plus
    out-of-bounds warnings for any shape whose bbox leaves the canvas.
    """
    defects: list[LayoutDefect] = []

    text_shapes = [
        s for s in slide.shapes
        if s.has_text_frame and s.text_frame.text.strip()
    ]

    # Pairwise text-shape overlap.
    for i, a in enumerate(text_shapes):
        for b in text_shapes[i + 1:]:
            if _overlaps(_bbox(a), _bbox(b)):
                defects.append(LayoutDefect(
                    kind="text-overlap",
                    slide_index=slide_index,
                    shape_a=_text_snippet(a),
                    shape_b=_text_snippet(b),
                    message=(
                        f"text shapes overlap: "
                        f"'{_text_snippet(a)}' ↔ '{_text_snippet(b)}'"
                    ),
                ))

    # Out-of-bounds: any shape extending past slide edges.
    for shape in slide.shapes:
        x1, y1, x2, y2 = _bbox(shape)
        if x1 < 0 or y1 < 0 or x2 > slide_w or y2 > slide_h:
            defects.append(LayoutDefect(
                kind="out-of-bounds",
                slide_index=slide_index,
                shape_a=_text_snippet(shape),
                shape_b=None,
                message=(
                    f"shape '{_text_snippet(shape)}' extends past slide edge "
                    f"(bbox: {x1},{y1} → {x2},{y2}; canvas: {slide_w}×{slide_h})"
                ),
            ))

    return defects


def validate_deck(prs) -> dict[int, list[LayoutDefect]]:
    """Walk every slide. Returns {slide_index: defects} for slides with issues."""
    out: dict[int, list[LayoutDefect]] = {}
    for i, slide in enumerate(prs.slides, start=1):
        d = validate_slide(
            slide,
            slide_index=i,
            slide_w=prs.slide_width,
            slide_h=prs.slide_height,
        )
        if d:
            out[i] = d
    return out


def format_defects(defects_by_slide: dict[int, list[LayoutDefect]]) -> str:
    """Human-readable summary for printing after build."""
    if not defects_by_slide:
        return "layout validator: clean — no overlaps, no out-of-bounds."
    lines = [
        f"layout validator: {sum(len(v) for v in defects_by_slide.values())} "
        f"defect(s) across {len(defects_by_slide)} slide(s)"
    ]
    for slide_idx in sorted(defects_by_slide):
        for d in defects_by_slide[slide_idx]:
            lines.append(f"  {d}")
    return "\n".join(lines)


# ============================================================================
# Diagram defect classes — three deterministic checks on picture nodes that
# carry _diagram_meta from expand_diagram_blocks.
# ============================================================================

def validate_diagrams(
    nodes,
    *,
    slide_index: int,
    slide_w: int,
    slide_h: int,
) -> list[LayoutDefect]:
    """diagram-overflow: any internal primitive bbox escapes its canvas.

    When the diagram block declared `virtual:WxH`, primitives are authored
    in virtual coords (e.g. 0..6880) and the renderer rasterizes the full
    virtual canvas before PowerPoint downscales on insert. The overflow
    check therefore compares against the *virtual* canvas, not the slot.
    Legacy blocks (no `virtual:`) have virtual_canvas_w == slot_w, so the
    behavior is unchanged.
    """
    defects: list[LayoutDefect] = []

    diagram_pics = [
        n for n in nodes
        if getattr(n, "kind", None) == "picture"
        and "_diagram_meta" in getattr(n, "kw_args", {})
    ]

    for pic in diagram_pics:
        meta = pic.kw_args["_diagram_meta"]
        canvas_w = meta.get("virtual_canvas_w", pic.kw_args["w"])
        canvas_h = meta.get("virtual_canvas_h", pic.kw_args["h"])
        prim_id = pic.kw_args.get("id", "?")

        for prim in meta["internal_primitives"]:
            px, py, pw, ph = prim["x"], prim["y"], prim["w"], prim["h"]
            if (px < 0 or py < 0
                    or px + pw > canvas_w
                    or py + ph > canvas_h):
                defects.append(LayoutDefect(
                    kind="diagram-overflow",
                    slide_index=slide_index,
                    shape_a=f"{prim_id}.{prim['id']}",
                    shape_b=None,
                    message=(
                        f"diagram '{prim_id}': '{prim['id']}' "
                        f"bbox ({px},{py},{pw}x{ph}) exceeds "
                        f"canvas {canvas_w}x{canvas_h}"
                    ),
                ))
    return defects


def validate_diagrams_color(
    nodes,
    *,
    slide_index: int,
    brand_dir: Path,
) -> list[LayoutDefect]:
    """diagram-color-mismatch: rendered color not in active brand's tokens."""
    from lib.diagrams.brand_bridge import SEMANTIC_NAMES, resolve, BrandBridgeError
    palette: set[str] = set()
    for sem in SEMANTIC_NAMES:
        try:
            palette.add(resolve(sem, brand_dir).lower())
        except BrandBridgeError:
            pass

    defects: list[LayoutDefect] = []
    diagram_pics = [
        n for n in nodes
        if getattr(n, "kind", None) == "picture"
        and "_diagram_meta" in getattr(n, "kw_args", {})
    ]

    import re as _re
    for pic in diagram_pics:
        src = pic.kw_args.get("src")
        if not src:
            continue
        png_path = Path(src)
        # Look for sibling .svg or .excalidraw artifact
        artifact_path = png_path.with_suffix(".svg")
        if not artifact_path.exists():
            artifact_path = png_path.with_suffix(".excalidraw")
        if not artifact_path.exists():
            continue
        text = artifact_path.read_text()
        for m in _re.finditer(r"#[0-9a-fA-F]{6}", text):
            color = m.group(0).lower()
            if color not in palette:
                defects.append(LayoutDefect(
                    kind="diagram-color-mismatch",
                    slide_index=slide_index,
                    shape_a=pic.kw_args.get("id", "?"),
                    shape_b=None,
                    message=(
                        f"diagram '{pic.kw_args.get('id', '?')}' uses "
                        f"non-brand color {m.group(0)}"
                    ),
                ))
                break  # one per diagram
    return defects


_MIN_PT: dict[str, int] = {
    "title": 18,
    "subtitle": 14,
    "body": 12,
    "value": 10,
    "detail": 10,
    "axis-label": 9,
}


def validate_diagrams_text_size(
    nodes,
    *,
    slide_index: int,
    slide_w: int,
    slide_h: int,
) -> list[LayoutDefect]:
    """diagram-text-too-small: effective on-slide font size < min for role.

    When the diagram block uses `virtual:WxH`, the body's font_size is in
    virtual-canvas coords. The rendered PNG is then downscaled by
    PowerPoint from the virtual canvas to the slot. Effective on-slide pt:

        on_slide_pt = font_size
                      * (slot_w / virtual_canvas_w)   # downscale on insert
                      * (slot_w / slide_w)            # region/slide ratio

    For legacy blocks (no `virtual:`) virtual_canvas_w == slot_w so the
    first factor is 1.0 and the original formula is preserved.
    """
    defects: list[LayoutDefect] = []
    diagram_pics = [
        n for n in nodes
        if getattr(n, "kind", None) == "picture"
        and "_diagram_meta" in getattr(n, "kw_args", {})
    ]

    for pic in diagram_pics:
        meta = pic.kw_args["_diagram_meta"]
        region_w = pic.kw_args["w"]
        virtual_w = meta.get("virtual_canvas_w", region_w)
        # Downscale factor PowerPoint applies on insert (1.0 when no virtual).
        downscale = region_w / max(virtual_w, 1)
        # Region-to-slide ratio (existing semantics).
        ratio = region_w / max(slide_w, 1)
        for prim in meta["internal_primitives"]:
            if prim["kind"] != "text":
                continue
            role = prim.get("role") or "body"
            min_pt = _MIN_PT.get(role, 12)
            font_size = prim.get("font_size") or 14.0
            on_slide_pt = font_size * downscale * ratio
            if on_slide_pt < min_pt:
                defects.append(LayoutDefect(
                    kind="diagram-text-too-small",
                    slide_index=slide_index,
                    shape_a=f"{pic.kw_args.get('id', '?')}.{prim['id']}",
                    shape_b=None,
                    message=(
                        f"diagram '{pic.kw_args.get('id', '?')}': "
                        f"'{prim['id']}' renders at {on_slide_pt:.1f}pt, "
                        f"below {min_pt}pt for role={role}"
                    ),
                ))
    return defects
