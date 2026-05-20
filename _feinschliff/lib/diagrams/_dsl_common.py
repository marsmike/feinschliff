"""Shared constants and helpers used by every diagram-DSL pipeline stage.

`excalidraw_expand`, `svg_expand`, and `diagram_wireframe` all need the
canvas-scale rule, coordinate parsing, and color resolution to agree
exactly — the wireframe-pass validator compares against the size the
renderer emits, so any drift between expander and validator silently
flags real overflow as a false positive (or hides a real one). Keep
this module dependency-light so all three importers can use it
without circularity.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


DIAGRAM_SLOT_BASELINE = 1720  # both narrow and full diagram slots are 1720 px wide


def canvas_scale(canvas_w: int | None) -> float:
    """Multiplier for default font/stroke sizes when authoring in a
    virtual viewport.

    The scale is derived from the diagram-slot baseline (1720 px), not
    the slide-pixel baseline (1920 px) — what matters for legibility is
    how the rendered PNG downscales into the slot, not the slot's
    fractional position within the slide. For a 6880-wide virtual canvas
    inserted into a 1720-wide slot this yields scale=4.0 exactly, so a
    16-px box label renders as 64 px in the SVG, 16 px on slide after
    PowerPoint's downscale — matching the legacy narrow-canvas size.

    Canvases ≤ the slot baseline return 1.0 so legacy small-canvas
    examples (800-, 1280-wide) keep their existing behavior bit-for-bit
    (PowerPoint stretches their renders up; fonts grow naturally)."""
    if not canvas_w or canvas_w <= DIAGRAM_SLOT_BASELINE:
        return 1.0
    return canvas_w / float(DIAGRAM_SLOT_BASELINE)


# ─── Coordinate parsing ───────────────────────────────────────────────────


def parse_xy(s: str) -> tuple[int, int]:
    """Parse an `X,Y` coordinate pair from a DSL token. Accepts floats
    but truncates to ints (DSL coords are pixel-aligned at emit time)."""
    x, y = s.split(",")
    return int(float(x)), int(float(y))


def parse_wh(s: str) -> tuple[int, int]:
    """Parse a `WxH` size pair from a DSL token."""
    w, h = s.split("x")
    return int(float(w)), int(float(h))


@dataclass
class Canvas:
    w: int
    h: int


_CANVAS_RE = re.compile(r"canvas\s+(\d+)x(\d+)")


def parse_canvas(line: str) -> Canvas:
    """Parse a `canvas WxH` directive. Raises ValueError on malformed input."""
    m = _CANVAS_RE.match(line)
    if not m:
        raise ValueError(f"bad canvas line: {line!r}")
    return Canvas(int(m.group(1)), int(m.group(2)))


# ─── Sizing ───────────────────────────────────────────────────────────────


def scaled_int(base: float, scale: float) -> int:
    """Scale a default font / stroke value by the canvas-scale multiplier,
    clamping to a minimum of 1 so even very small bases don't disappear."""
    return max(1, int(round(base * scale)))
