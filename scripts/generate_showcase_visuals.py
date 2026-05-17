#!/usr/bin/env python3
"""Generate hero grid + animated GIF from the Feinschliff showcase HTML.

Run via:
    cd scripts/
    uv venv && source .venv/bin/activate
    uv pip install playwright pillow
    playwright install chromium
    uv run python generate_showcase_visuals.py

Outputs:
    feinschliff/docs/images/slides/slide-NN.png  (intermediate, gitignored)
    feinschliff/docs/images/hero-grid.png        (committed)
    feinschliff/docs/images/showcase.gif         (committed)
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HTML_PATH = (
    REPO_ROOT
    / "feinschliff"
    / "brands"
    / "feinschliff"
    / "claude-design"
    / "feinschliff-2026.html"
)
IMAGES_DIR = REPO_ROOT / "feinschliff" / "docs" / "images"
SLIDES_DIR = IMAGES_DIR / "slides"


# --- Hero grid configuration -------------------------------------------------
# Indices here map onto slide-NN.png produced by render_slides().
# Picked across the deck for visual variety: cover (orange), kpi grid, two-col,
# big number, quote-ish, and an end card. Adjust if a particular index is
# visually weak after a first pass.
HERO_PICKS = [0, 6, 12, 18, 24, 30]
HERO_COLS = 3
HERO_ROWS = 2
HERO_GAP = 24
HERO_THUMB_W = 720
HERO_BG = (242, 244, 248)  # --fs-paper

# --- GIF configuration -------------------------------------------------------
GIF_PICKS = [0, 4, 8, 12, 16, 20, 24, 28]
GIF_WIDTH = 900
GIF_DURATION_MS = 2000
GIF_COLORS = 96  # palette size (smaller = smaller file)


async def render_slides() -> list[Path]:
    """Render every <section> in the deck-stage HTML to a PNG.

    Uses the `noscale` attribute on <deck-stage> so all slides become visible
    at their authored 1920x1080 size — the deck-stage web component normally
    hides non-active slides.
    """
    from playwright.async_api import async_playwright

    SLIDES_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=2,
        )
        page = await ctx.new_page()
        await page.goto(f"file://{HTML_PATH}", wait_until="networkidle")
        # Allow webfonts + layout to settle.
        await page.wait_for_timeout(2500)

        # Hide deck-stage chrome (slide counter overlay, validator badge,
        # validator panel) so screenshots show only the slide canvas.
        await page.add_style_tag(
            content="""
            #dc-validator, #dc-validator-toggle { display: none !important; }
            """
        )
        await page.evaluate(
            """
            const stage = document.querySelector('deck-stage');
            if (stage && stage.shadowRoot) {
              const s = document.createElement('style');
              s.textContent = '.overlay, .tapzones { display: none !important; }';
              stage.shadowRoot.appendChild(s);
            }
            """
        )

        # Count slides up front.
        total = await page.evaluate(
            """document.querySelectorAll('deck-stage > section').length"""
        )
        print(f"Found {total} slides")

        rendered: list[Path] = []
        for i in range(total):
            # Navigate via the deck-stage public API, then screenshot the
            # viewport. Each slide is the only visible one, scaled to fit
            # 1920x1080 viewport — perfect for screenshots.
            await page.evaluate(
                f"""
                (async () => {{
                  const stage = document.querySelector('deck-stage');
                  // Set index directly via the internal _go method.
                  if (typeof stage._go === 'function') {{
                    stage._go({i}, 'api');
                  }} else {{
                    // Fallback: toggle data-deck-active manually.
                    const slides = document.querySelectorAll('deck-stage > section');
                    slides.forEach((s, idx) => {{
                      if (idx === {i}) s.setAttribute('data-deck-active', '');
                      else s.removeAttribute('data-deck-active');
                    }});
                  }}
                }})();
                """
            )
            # Tiny pause for any transitions / lazy content to settle.
            await page.wait_for_timeout(120)
            target = SLIDES_DIR / f"slide-{i:02d}.png"
            await page.screenshot(path=str(target), full_page=False)
            rendered.append(target)
            print(f"  -> {target.name}")

        await browser.close()
        return rendered


def build_hero_grid(rendered: list[Path]) -> Path:
    from PIL import Image

    picks = [SLIDES_DIR / f"slide-{i:02d}.png" for i in HERO_PICKS]
    missing = [p for p in picks if not p.exists()]
    if missing:
        raise SystemExit(f"Missing slide PNGs for hero grid: {missing}")

    imgs = []
    for p in picks:
        src = Image.open(p)
        w, h = src.size
        new_h = int(h * HERO_THUMB_W / w)
        imgs.append(src.resize((HERO_THUMB_W, new_h), Image.LANCZOS))

    thumb_h = imgs[0].height
    total_w = HERO_COLS * HERO_THUMB_W + (HERO_COLS + 1) * HERO_GAP
    total_h = HERO_ROWS * thumb_h + (HERO_ROWS + 1) * HERO_GAP
    canvas = Image.new("RGB", (total_w, total_h), HERO_BG)
    for idx, img in enumerate(imgs):
        r = idx // HERO_COLS
        c = idx % HERO_COLS
        x = HERO_GAP + c * (HERO_THUMB_W + HERO_GAP)
        y = HERO_GAP + r * (thumb_h + HERO_GAP)
        canvas.paste(img, (x, y))

    out = IMAGES_DIR / "hero-grid.png"
    canvas.save(out, optimize=True)
    print(f"hero-grid: {out}  ({out.stat().st_size // 1024} KB, {total_w}x{total_h})")
    return out


def build_gif(rendered: list[Path]) -> Path:
    from PIL import Image

    picks = [SLIDES_DIR / f"slide-{i:02d}.png" for i in GIF_PICKS]
    available = [p for p in picks if p.exists()]
    if not available:
        raise SystemExit("No slide PNGs available for GIF")

    frames = []
    for p in available:
        img = Image.open(p).convert("RGB")
        w, h = img.size
        new_h = int(h * GIF_WIDTH / w)
        resized = img.resize((GIF_WIDTH, new_h), Image.LANCZOS)
        frames.append(
            resized.convert("P", palette=Image.ADAPTIVE, colors=GIF_COLORS)
        )

    out = IMAGES_DIR / "showcase.gif"
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=GIF_DURATION_MS,
        loop=0,
        optimize=True,
        disposal=2,
    )
    size_kb = out.stat().st_size // 1024
    print(f"showcase.gif: {out}  ({size_kb} KB, {len(frames)} frames)")
    if size_kb > 5 * 1024:
        print("WARNING: showcase.gif > 5 MB — consider reducing GIF_WIDTH or GIF_COLORS")
    return out


async def main() -> int:
    if not HTML_PATH.exists():
        print(f"HTML not found: {HTML_PATH}", file=sys.stderr)
        return 1

    rendered = await render_slides()
    if not rendered:
        print("No slides rendered.", file=sys.stderr)
        return 1

    build_hero_grid(rendered)
    build_gif(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
