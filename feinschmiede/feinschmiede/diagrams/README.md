# Diagram engine

Shared diagram pipeline for feinschliff DSL and the feinbild plugin. Two
front-end syntaxes (Excalidraw, SVG) compile through a common AST to one
of two renderers.

## DSL primitives (Excalidraw)

Source: [`excalidraw_expand.py`](excalidraw_expand.py).

| Primitive | Notes |
|---|---|
| `box`, `ellipse`, `diamond`, `dot` | shapes; fill, stroke, label |
| `line` | with optional `dashed` flag |
| `arrow` | with optional `label:"…"` |
| `text` | levels: `title`, `subtitle`, `eyebrow`, `body`, `detail`, `mono` |
| `theme dark` | flips to dark canvas |
| `group` | logical grouping |

- `\n` inside a quoted label becomes a real newline.
- Label color flips to `paper` on dark fills (luminance check).

## Color tokens

Resolved via `brand_bridge.resolve()` (`brand_bridge.py`). Upstream
Excalidraw color aliases map to brand tokens:

`start` · `end` · `decision` · `ai` · `inactive` · `error` · `code` · `data`

So a DSL written against upstream names still themes correctly under any
brand pack.

## Arrow routing

Edge-to-edge straight line along the center-to-center ray (matches
upstream Excalidraw's `make_arrow`). **No Z-elbows, no collision
avoidance** — author places boxes so straight arrows have room.

## Render dispatcher

[`render.py`](render.py) tries the rough path first, then falls back:

1. **`render_rough`** (preferred). Pure-Python: `rough` port +
   `cairosvg`. ~150 ms, no browser. Run with
   `roughness=0 + disableMultiStroke=True` for the clean "normal"
   Excalidraw look.
2. **`render_playwright`** (fallback). Real Excalidraw web app in
   headless Chromium. ~1.5 s + 200 MB. Used when the rough path is
   unavailable or the document contains elements the Python port
   doesn't model (freedraw, image, frame).

## See also

- Cache-key + validator parity rules live in the repo `CLAUDE.md` under
  "Diagram pipeline" — those are AI-contributor invariants, not engine
  internals.
