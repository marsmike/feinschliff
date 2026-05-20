"""Walk a PPTX slide's shape tree → ExtractedDiagram (lossless, deterministic)."""
from __future__ import annotations

from .ir import ExtractedDiagram, Node, Edge


_SHAPE_TYPE_MAP = {
    1: "rect",       # MSO_SHAPE.RECTANGLE
    9: "ellipse",    # MSO_SHAPE.OVAL
    13: "diamond",   # MSO_SHAPE.DIAMOND
}


def extract_from_slide(
    slide,
    *,
    target_w: int = 1720,
    target_h: int = 480,
) -> ExtractedDiagram:
    """Walk python-pptx slide.shapes, emit IR. Confidence is always 1.0.

    Coordinates are scaled from the source slide's EMU space into the
    target region (default 1720x480, matching feinschliff's diagram region).
    """
    nodes: list[Node] = []
    edges: list[Edge] = []
    has_arrows = False

    # Read source slide dimensions in EMU so coords can be scaled to the
    # target diagram region. python-pptx exposes these on the parent
    # presentation_part.
    try:
        prs = slide.part.package.presentation_part.presentation
        slide_w_emu = prs.slide_width or 9144000
        slide_h_emu = prs.slide_height or 6858000
    except AttributeError:
        slide_w_emu = 9144000  # default 10in widescreen
        slide_h_emu = 6858000

    x_scale = target_w / slide_w_emu
    y_scale = target_h / slide_h_emu

    for idx, shape in enumerate(slide.shapes):
        # python-pptx raises ValueError when accessing auto_shape_type on
        # shapes that aren't auto-shapes (textboxes, pictures, group shapes).
        # Treat those as non-diagram primitives and skip silently.
        try:
            auto_type = shape.auto_shape_type
        except (ValueError, AttributeError):
            auto_type = None
        if auto_type is not None and int(auto_type) in _SHAPE_TYPE_MAP:
            kind = _SHAPE_TYPE_MAP[int(auto_type)]
            label = ""
            if shape.has_text_frame and shape.text_frame.text:
                label = shape.text_frame.text.strip().split("\n")[0]
            nodes.append(Node(
                id=f"n{idx}",
                label=label,
                type=kind,
                x=int((shape.left or 0) * x_scale),
                y=int((shape.top or 0) * y_scale),
                w=int((shape.width or 0) * x_scale),
                h=int((shape.height or 0) * y_scale),
            ))
        elif _is_connector(shape):
            has_arrows = True
            # python-pptx does not expose begin/end connection ids directly;
            # fall back gracefully rather than emitting unresolvable "?" ids.
            from_id = getattr(shape, "begin_connection_shape_id", None)
            to_id = getattr(shape, "end_connection_shape_id", None)
            if from_id and to_id:
                edges.append(Edge(
                    from_id=from_id,
                    to_id=to_id,
                    kind="arrow",
                ))

    signals = {
        "boxes_and_arrows": (len(nodes) >= 2 and (has_arrows or len(edges) > 0)),
        "bars": False,
        "axis": False,
        "freeform": False,
    }
    return ExtractedDiagram(
        nodes=nodes, edges=edges, signals=signals, confidence=1.0,
    )


def _is_connector(shape) -> bool:
    # MSO_SHAPE_TYPE.LINE = 9 (but auto_shape_type is None for connectors)
    return getattr(shape, "shape_type", None) == 9
