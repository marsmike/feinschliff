"""Render diagram artifacts to PNG.

Supported inputs:
  .svg          → cairosvg (primary); playwright (fallback)
  .excalidraw   → render_rough + cairosvg (primary, pure-Python);
                  render_playwright (fallback, full-fidelity Chromium)

A single render() entry point dispatches by extension.

For `.excalidraw`, the primary path uses the `rough` Python port + cairosvg
to emit clean (roughness=0) SVG and rasterize it — no browser, ~150ms per
diagram. If `rough` or `cairosvg` aren't installed, or the document uses
elements the Python translator can't represent (freedraw / image / frame),
the renderer falls through to Playwright + the real Excalidraw web app
bundled at `playwright_assets/render_template.html`. That path is heavier
(~200MB Chromium, ~1.5s cold) but covers every Excalidraw element type.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _ensure_libcairo_on_macos() -> None:
    """Make Homebrew's libcairo discoverable by cairocffi/cairosvg.

    uv-managed Python on macOS doesn't see `/opt/homebrew/opt/cairo/lib`
    by default; cairocffi then OSErrors at import time and the renderer
    silently falls through to Playwright. Probe the canonical Homebrew
    path and prepend it to DYLD_FALLBACK_LIBRARY_PATH so rough is the
    real default. No-op on non-macOS or when cairo isn't installed.
    """
    if sys.platform != "darwin":
        return
    cairo_lib = "/opt/homebrew/opt/cairo/lib"
    if not Path(cairo_lib, "libcairo.2.dylib").exists():
        return
    existing = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    if cairo_lib in existing.split(":"):
        return
    os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = (
        f"{cairo_lib}:{existing}" if existing else cairo_lib
    )


_ensure_libcairo_on_macos()


def render(src: Path, out: Path) -> Path:
    ext = src.suffix.lower()
    if ext == ".svg":
        return _render_svg(src, out)
    if ext == ".excalidraw":
        return _render_excalidraw(src, out)
    raise ValueError(f"render: unsupported format {ext!r}")


def _render_svg(src: Path, out: Path) -> Path:
    try:
        import cairosvg
        cairosvg.svg2png(url=str(src), write_to=str(out))
        return out
    except (ImportError, OSError):
        return _render_svg_playwright(src, out)


_SVG_DIM_RE = __import__("re").compile(
    r'<svg\b[^>]*?\bwidth="(\d+(?:\.\d+)?)"[^>]*?\bheight="(\d+(?:\.\d+)?)"',
    flags=__import__("re").IGNORECASE | __import__("re").DOTALL,
)
_SVG_VIEWBOX_RE = __import__("re").compile(
    r'<svg\b[^>]*?\bviewBox="\s*-?\d+(?:\.\d+)?\s+-?\d+(?:\.\d+)?\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)"',
    flags=__import__("re").IGNORECASE | __import__("re").DOTALL,
)


def _svg_dimensions(svg_text: str) -> tuple[int, int]:
    """Best-effort parse of the SVG's intrinsic size for the Playwright viewport.

    Falls back to viewBox dimensions, then a 1600x900 default. Returns ints
    suitable for page.set_viewport_size.
    """
    m = _SVG_DIM_RE.search(svg_text)
    if m:
        return int(float(m.group(1))), int(float(m.group(2)))
    m = _SVG_VIEWBOX_RE.search(svg_text)
    if m:
        return int(float(m.group(1))), int(float(m.group(2)))
    return 1600, 900


def _render_svg_playwright(src: Path, out: Path) -> Path:
    from playwright.sync_api import sync_playwright

    svg_text = src.read_text()
    width, height = _svg_dimensions(svg_text)
    html = (
        f"<html><body style='margin:0;padding:0'>"
        f"{svg_text}"
        f"</body></html>"
    )
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_viewport_size({"width": width, "height": height})
        page.set_content(html)
        page.screenshot(path=str(out), full_page=True, omit_background=True,
                        clip={"x": 0, "y": 0, "width": width, "height": height})
        browser.close()
    return out


def _render_excalidraw(src: Path, out: Path) -> Path:
    """Render Excalidraw JSON → PNG. rough (pure Python) first; Playwright
    fallback when rough/cairosvg can't handle the document.

    The chain is structured so production builds never hard-fail just
    because Playwright isn't installed: as long as cairosvg + rough are
    available (both in the runtime dep set), the primary path covers the
    full Feinschliff diagram vocabulary (rectangle / ellipse / diamond /
    line / arrow / text / dot / group). The Playwright fallback only
    kicks in for documents containing elements rough doesn't model.
    """
    import sys
    try:
        from .render_rough import render_excalidraw as _r_rough
        return _r_rough(src, out, style="clean")
    except (ImportError, OSError, NotImplementedError) as exc:
        print(
            f"render: rough/cairosvg path unavailable ({exc.__class__.__name__}: "
            f"{exc}); falling back to Playwright.",
            file=sys.stderr,
        )
    except Exception as exc:
        # rough handles its own warnings for unknown element types, but a hard
        # raise (bad JSON, totally unsupported document) still warrants a try
        # at Playwright before surfacing the failure to the caller.
        print(
            f"render: rough path raised {exc.__class__.__name__} — trying "
            f"Playwright fallback.",
            file=sys.stderr,
        )

    try:
        from .render_playwright import render_excalidraw as _r_pw
        return _r_pw(src, out)
    except ImportError as exc:
        raise RuntimeError(
            "render: both rendering backends unavailable. Install either "
            "`rough` + `cairosvg` (preferred, pure-Python) OR `playwright` "
            "with chromium (`uv run playwright install chromium`)."
        ) from exc


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(prog="python -m lib.diagrams.render")
    parser.add_argument("input", type=Path, help="Path to .svg or .excalidraw source")
    parser.add_argument("-o", "--out", type=Path, help="Output .png path (default: <input>.png)")
    args = parser.parse_args(argv)

    out = args.out or args.input.with_suffix(".png")
    render(args.input, out)
    print(f"render: wrote {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
