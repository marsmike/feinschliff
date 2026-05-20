"""Render Excalidraw JSON to PNG via the official @excalidraw/excalidraw
ESM bundle inside headless Chromium.

The renderer loads ``playwright_assets/render_template.html`` (which imports
``@excalidraw/excalidraw`` from esm.sh and exposes ``window.renderToSvg``),
feeds it the scene payload, then screenshots the inline ``<svg>`` that the
official ``exportToSvg`` helper produces. The result matches what
excalidraw.com's "Export to SVG" emits — full rough.js handlines, browser
text metrics, native arrow rendering, every element type the Excalidraw web
app supports.

First-time setup (per machine)::

    uv pip install playwright
    uv run playwright install chromium

Cost: ~1.5 s for the Chromium cold-start, ~500 ms per render once the
browser is warm.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

_TEMPLATE = Path(__file__).parent / "playwright_assets" / "render_template.html"
_VIEWPORT_FALLBACK = (1280, 800)
_EMPTY_CANVAS = (0.0, 0.0, 800.0, 600.0)
_BBOX_PAD = 80


def _element_extents(elements: Iterable[dict]) -> list[tuple[float, float, float, float]]:
    """Per non-deleted element, return its (x0, y0, x1, y1) axis-aligned rect.

    Arrows and lines carry an optional ``points`` array whose entries are
    relative to the element's ``x``/``y``. The element's nominal
    ``width``/``height`` doesn't always cover that path (Excalidraw allows
    width=0 lines with non-trivial points), so for those types we derive
    the rect from the points themselves instead.
    """
    rects: list[tuple[float, float, float, float]] = []
    for el in elements:
        if el.get("isDeleted"):
            continue
        ox = float(el.get("x", 0))
        oy = float(el.get("y", 0))
        if el.get("type") in ("arrow", "line") and el.get("points"):
            xs = [ox + float(px) for px, _ in el["points"]]
            ys = [oy + float(py) for _, py in el["points"]]
            rects.append((min(xs), min(ys), max(xs), max(ys)))
            continue
        w = abs(float(el.get("width", 0)))
        h = abs(float(el.get("height", 0)))
        rects.append((ox, oy, ox + w, oy + h))
    return rects


def _scene_bbox(elements: list[dict]) -> tuple[float, float, float, float]:
    """Union of all element extents in the scene. Falls back to a fixed
    800×600 canvas when no element contributes a rect — matches what the
    Excalidraw web app shows for an empty scene."""
    rects = _element_extents(elements)
    if not rects:
        return _EMPTY_CANVAS
    x0s, y0s, x1s, y1s = zip(*rects)
    return (min(x0s), min(y0s), max(x1s), max(y1s))


def render_excalidraw(
    src: Path,
    out: Path,
    *,
    scale: int = 2,
    max_width: int = 1920,
) -> Path:
    """Render the ``.excalidraw`` JSON at ``src`` to a PNG at ``out``.

    Sizing notes (subtle — please don't "simplify" without reading):

    - Excalidraw's ``exportToSvg`` returns a ``<svg>`` whose ``width`` and
      ``height`` attributes are set to **2× the viewBox dimensions** as a
      built-in HiDPI hint. The element's CSS-rendered bounding rect is
      therefore ``2 × (diagram_w × diagram_h)``. If the viewport is
      smaller than that bounding rect, Chromium does not lay out the
      off-viewport portion of the SVG, and ``screenshot()`` captures only
      the laid-out portion — content past the viewport renders as blank
      white pixels (this is the "bottom half is white" bug we hit on the
      ``-full`` deep diagrams).
    - Chromium also caps any single raster surface at roughly 268M
      pixels. ``viewport × device_scale_factor²`` must stay under that
      ceiling or the rasterizer clips again. For a 6880×2880 virtual
      canvas Excalidraw renders into a ~13760×5760 CSS box; at DPR=2 the
      backing surface is ~317M pixels — over the cap. So we keep DPR=1
      and let the output land at the SVG's natural viewBox resolution
      (which is our target: it matches the virtual canvas, and PowerPoint
      downscales on insert into the slot).

    The ``scale`` / ``max_width`` kwargs are kept for API compatibility
    but are intentionally ignored — see the rationale above.
    """
    from playwright.sync_api import sync_playwright

    del scale, max_width  # see docstring — Chromium-pixel-cap + Excalidraw 2× scaling

    scene = json.loads(src.read_text(encoding="utf-8"))
    live = [e for e in scene.get("elements", []) if not e.get("isDeleted")]
    if not live:
        raise ValueError(f"render_playwright: scene at {src} has no renderable elements")

    x0, y0, x1, y1 = _scene_bbox(live)
    diagram_w = (x1 - x0) + _BBOX_PAD * 2
    diagram_h = (y1 - y0) + _BBOX_PAD * 2

    # Excalidraw's exportToSvg sets the SVG's attribute width/height at
    # 2× the viewBox. The CSS bounding rect is therefore 2× the diagram;
    # the viewport must contain that or Chromium leaves the overflow
    # blank. The +margin absorbs the inline-block stage's own padding.
    css_scale = 2
    margin = 64
    fb_w, fb_h = _VIEWPORT_FALLBACK
    vp_w = max(int(diagram_w * css_scale) + margin, fb_w)
    vp_h = max(int(diagram_h * css_scale) + margin, fb_h)

    out.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(
                viewport={"width": vp_w, "height": vp_h},
                device_scale_factor=1,
            )
            page.goto(_TEMPLATE.as_uri())
            page.wait_for_function(
                "document.body.dataset.state === 'ready'", timeout=30_000
            )
            result = page.evaluate("payload => window.renderToSvg(payload)", scene)
            if not result or not result.get("ok"):
                err = (result or {}).get("error", "exportToSvg returned no payload")
                raise RuntimeError(f"render_playwright: {err}")
            page.wait_for_function(
                "document.body.dataset.state === 'rendered'", timeout=15_000
            )
            stage_svg = page.query_selector("#stage svg")
            if stage_svg is None:
                raise RuntimeError("render_playwright: no <svg> attached to #stage after render")
            stage_svg.screenshot(path=str(out))
        finally:
            browser.close()

    return out
