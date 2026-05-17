"""High-fidelity Excalidraw → PNG via Playwright + real Excalidraw web app.

Loads the bundled `playwright_assets/render_template.html` (which imports
`@excalidraw/excalidraw` from esm.sh), feeds it the Excalidraw JSON, and
screenshots the rendered `<svg>` element. This produces output identical
to what excalidraw.com's "Export to SVG" emits — full rough.js handlines,
correct text wrapping (browser measureText), native arrow rendering, all
element types Excalidraw itself supports.

First-time setup (per machine):
    uv pip install playwright
    uv run playwright install chromium

Cost: ~200 MB chromium download, ~1.5 s cold start, ~500 ms per render
after the browser warms up.
"""
from __future__ import annotations

import json
from pathlib import Path

_TEMPLATE = Path(__file__).parent / "playwright_assets" / "render_template.html"


def _bbox(elements: list[dict]) -> tuple[float, float, float, float]:
    """Compute (min_x, min_y, max_x, max_y) across non-deleted elements."""
    mn_x = mn_y = float("inf")
    mx_x = mx_y = float("-inf")
    for el in elements:
        if el.get("isDeleted"):
            continue
        x, y = el.get("x", 0), el.get("y", 0)
        w, h = el.get("width", 0), el.get("height", 0)
        if el.get("type") in ("arrow", "line") and "points" in el:
            for px, py in el["points"]:
                mn_x, mn_y = min(mn_x, x + px), min(mn_y, y + py)
                mx_x, mx_y = max(mx_x, x + px), max(mx_y, y + py)
        else:
            mn_x, mn_y = min(mn_x, x), min(mn_y, y)
            mx_x, mx_y = max(mx_x, x + abs(w)), max(mx_y, y + abs(h))
    if mn_x == float("inf"):
        return (0.0, 0.0, 800.0, 600.0)
    return (mn_x, mn_y, mx_x, mx_y)


def render_excalidraw(
    src: Path,
    out: Path,
    *,
    scale: int = 2,
    max_width: int = 1920,
) -> Path:
    """Render `.excalidraw` JSON at `src` to PNG at `out`. Raises if Playwright
    or Chromium isn't available — caller handles the fallback decision.

    Sizing notes (subtle — please don't "simplify" without reading):

    - Excalidraw's ``exportToSvg`` returns a `<svg>` with `width`/`height`
      attributes set to **2× the viewBox dimensions** (its built-in HiDPI
      hint). The element's CSS-rendered bounding rect therefore equals
      `2 × (diagram_w × diagram_h)`. If the viewport is smaller than this
      bounding rect, Chromium does NOT lay out the off-viewport portion of
      the SVG, and ``svg_el.screenshot()`` captures the laid-out portion
      only — content beyond the viewport renders as blank white pixels.
      (This is what produced the "bottom half is white" bug on the
      ``-full`` deep diagrams.)
    - Chromium also caps any single raster surface at roughly 268M
      pixels. ``viewport × device_scale_factor²`` must stay under that
      ceiling or Chromium clips, again. For a 6880×2880 virtual canvas
      Excalidraw renders into a ~13760×5760 CSS box; at DPR=2 the
      backing surface is ~317M pixels — over the cap. So we keep DPR=1
      and let the output land at the SVG's natural viewBox resolution
      (which IS our target — it matches the virtual canvas, and
      PowerPoint downscales on insert into the slot).

    The ``scale`` / ``max_width`` kwargs are kept for API compatibility
    but are intentionally ignored — see the rationale above.
    """
    from playwright.sync_api import sync_playwright

    del scale, max_width  # see docstring — Chromium-pixel-cap + Excalidraw 2× scaling

    data = json.loads(src.read_text(encoding="utf-8"))
    elements = [e for e in data.get("elements", []) if not e.get("isDeleted")]
    if not elements:
        raise ValueError(f"render_playwright: no elements in {src}")

    mn_x, mn_y, mx_x, mx_y = _bbox(elements)
    pad = 80
    diagram_w = mx_x - mn_x + pad * 2
    diagram_h = mx_y - mn_y + pad * 2

    # Viewport must contain Excalidraw's 2× CSS-sized SVG. Add a small
    # margin to absorb the body's `display: inline-block` padding.
    _EXC_CSS_SCALE = 2
    _VP_MARGIN = 64
    vp_width = max(int(diagram_w * _EXC_CSS_SCALE) + _VP_MARGIN, 1280)
    vp_height = max(int(diagram_h * _EXC_CSS_SCALE) + _VP_MARGIN, 800)

    template_url = _TEMPLATE.as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(
                viewport={"width": vp_width, "height": vp_height},
                device_scale_factor=1,
            )
            page.goto(template_url)
            page.wait_for_function("window.__moduleReady === true", timeout=30000)
            result = page.evaluate("data => window.renderDiagram(data)", data)
            if not result or not result.get("success"):
                raise RuntimeError(
                    "render_playwright: " + (result.get("error", "render failed") if result else "no result")
                )
            page.wait_for_function("window.__renderComplete === true", timeout=15000)
            svg_el = page.query_selector("#root svg")
            if svg_el is None:
                raise RuntimeError("render_playwright: no SVG element after render")
            svg_el.screenshot(path=str(out))
        finally:
            browser.close()

    return out
