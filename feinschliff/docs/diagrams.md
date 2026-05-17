# Diagrams in feinschliff

Brand-aware diagram authoring inside the feinschliff plugin. Two DSLs, one shared library, embeddable in any slide.

## Surfaces

- **Standalone authoring** — invoke `/svg` or `/excalidraw` to author a diagram outside any slide. Output: a self-contained `.svg` or `.excalidraw` file plus a rendered PNG.
- **Slide-embedded** — drop an `svg { … }` or `excalidraw { … }` block inside any `.slide.dsl` layout, or use one of the two new whole-slide layouts (`excalidraw-diagram.slide.dsl`, `svg-infographic.slide.dsl`).

Both surfaces share the same brand-aware color resolution, the same coordinate / canvas helpers (`lib/diagrams/_dsl_common.py`), and the same structural validator.

## Which DSL should I pick?

```
                  Excalidraw                       SVG
                  ──────────                       ───
   intent         concept · flow · architecture    data viz · custom infographic
   primitives     box · arrow · zone · lane        rect · path · bar · axis · brace
   editable       yes — round-trips through        no — XML / Figma / Illustrator
                  the Excalidraw app
   typical job    "where does the request go?"     "how does Q3 stack up?"
                  "what calls what?"               "where's the brace + callout?"
   when in doubt  …pick this one. Most diagrams    …pick this only when Excalidraw
                  are concept diagrams.            can't express what you need
                                                    (paths, gradients, chart-y bits).
```

**Decision tree:**

1. Does the diagram have **boxes connected by arrows**? → Excalidraw.
2. Does it need **arbitrary SVG paths, gradients, or chart-specific primitives** (`bar` / `axis` / `legend` / `area` / `brace` / `callout` / `swatch_grid`)? → SVG.
3. Will it be **edited later by humans dragging things around** in the Excalidraw app? → Excalidraw.
4. Is it a **stock chart** (bars, funnel, 2x2, pyramid, gantt)? → Neither — use the dedicated layout (`bar-chart`, `funnel`, `2x2-matrix`, `pyramid`, `gantt`). The two diagram DSLs are escape hatches for content the stock layouts can't render.

Excalidraw cannot model: arbitrary `<path d="...">`, gradients, patterns, masks, clip-paths, chart-axis primitives. SVG cannot round-trip through the Excalidraw app; once you author it, edits are XML or external SVG editor only.

## Brand resolution

Diagrams have **no own palette**. Every color in a diagram DSL is a semantic name that resolves against the active brand's `tokens.json` via `lib.diagrams.brand_bridge`.

17-name semantic vocabulary, fixed:

| Group | Names |
|---|---|
| Brand   | `primary`, `secondary`, `tertiary`, `accent` |
| Surface | `paper`, `ink`, `surface`, `surface-2` |
| Severity| `success`, `warning`, `danger` |
| Neutral | `neutral`, `neutral-soft`, `neutral-strong` |
| Status  | `status-on`, `status-off`, `status-pending` |

Literal hex / `rgb()` / `hsl()` are rejected at parse time.

### Brand selection precedence

1. `@brand <name>` directive at the top of the DSL.
2. `--brand <name>` CLI flag.
3. `FEINSCHLIFF_BRAND` env var.
4. `/deck` build context (when invoked inside a slide).
5. `feinschliff` default.

## DSL — SVG

Generates clean SVG; ideal for custom charts, stat-card grids, infographics.

```
canvas <W>x<H>
rect   <id> <x>,<y> <w>x<h> <color>
circle <id> <cx>,<cy> <r> <color>
line   <id> <x1>,<y1> <x2>,<y2> [<color>] [dashed]
text   <id> <x>,<y> <level> "<content>"
bar    <id> <x>,<y> <w>x<h> <color> [value:"<v>"]
axis   <id> horizontal|vertical <x>,<y> <length> "<labels>"
legend <id> <x>,<y> <color>:"<label>" [<color>:"<label>" ...]
```

`<level>` for text: `title` · `subtitle` · `body` · `detail` · `value`.

## DSL — Excalidraw

Generates Excalidraw JSON; ideal for concept flows, architectures, system diagrams. The output file is editable in the Excalidraw app.

```
canvas <W>x<H>
box     <id> <x>,<y> <w>x<h> "<label>" [fill:<color>]
ellipse <id> <x>,<y> <w>x<h> "<label>" [fill:<color>]
arrow   <from_id> -> <to_id>
text    <id> <x>,<y> "<content>" [size:title|body|detail]
```

## Slide-embed block primitives

Embed a diagram in any layout:

```
svg <id> <x>,<y> <w>x<h> [from:"<path>"] {
  <inline DSL body>
}

excalidraw <id> <x>,<y> <w>x<h> [from:"<path>"] {
  <inline DSL body>
}
```

Rules:
- The region (`<w>x<h>`) IS the canvas. Do NOT declare `canvas` inside the body.
- `from:` external file is mutually exclusive with the inline `{ ... }` body.
- Nested diagrams (svg inside excalidraw or vice versa) are forbidden.
- The inline body MUST be on its own line(s) after the opening `{` — not on the header line.

## Whole-slide layouts

Two layouts spend the whole canvas on a single diagram:

- `excalidraw-diagram.slide.dsl` — concept diagrams (architectures, flows).
- `svg-infographic.slide.dsl` — custom data viz / infographics.

Slot schema (both): `pgmeta`, `tracker`, `action_title`, `so_what`, `source`, plus a required `diagram_dsl` slot carrying the body.

## Refurbish (`/deck polish --refurbish-all`)

Convert old diagrams in a rough `.pptx` into editable, brand-perfect DSL:

- **Vector path** — when the input PPTX has structured shapes (rect, ellipse, connectors), walked deterministically by python-pptx. Confidence 1.0.
- **Raster path** — when the input is an embedded image, Claude vision identifies the structure. Lower confidence; user reviews.

The kind selector picks excalidraw (concept flow) vs SVG (data viz) based on detected signals.

Outputs:
- `<deck-out>/refurbished/slide-N.{exc.dsl|svg.dsl}` — emitted DSL artifacts.
- `<deck-out>/refurbish_report.md` — per-slide detection summary.

The refurbish flow fully rebuilds the output deck: extracted DSL artifacts are substituted back into the deck plan and rendered via `feinschliff deck build`, producing a `.pptx` where each refurbished slide uses the brand-perfect DSL diagram instead of the original embedded image.

## Verification

Two layers of deterministic check run at **build time** for every diagram, alongside the slide-level checks (`text-overlap`, `out-of-bounds`):

**A. DSL-level checks** — primitives inside the diagram body, before emit:

| Class | Check |
|---|---|
| `diagram-overflow` | An internal primitive bbox extends past the diagram region. |
| `diagram-color-mismatch` | A rendered color is not in the active brand's `tokens.json`. |
| `diagram-text-too-small` | Computed on-slide font size is below the per-role minimum. |

**B. Structural checks** (`lib/diagrams/structural_validator.py`) — run after emit, on the output `.excalidraw` JSON or `.svg` markup:

| Class | Applies to | Check |
|---|---|---|
| `diagram-overflow` | Excalidraw, SVG | text bound to a container exceeds the inner box / SVG primitive bbox lies outside viewBox |
| `diagram-shape-overlap` | Excalidraw | two non-text shapes overlap without nesting |
| `diagram-text-collision` | Excalidraw | two free-floating text elements overlap |
| `diagram-arrow-crossing` | Excalidraw | arrow segment crosses a non-endpoint shape (WARN — heuristic) |
| `diagram-invalid-file` | both | malformed JSON / SVG, missing required fields |

All are deterministic (no vision-LLM judgment). FATAL defects gate the build; WARN defects print but don't fail. The structural validator can also run standalone on any `.excalidraw` or `.svg` file:

```
feinschliff verify-diagram path/to/diagram.excalidraw
feinschliff verify-diagram path/to/diagram.svg
```

The full 14-class LLM verify pass (run by `/deck`) is a separate downstream step and covers rhetorical + visual defects across all slide content.

## What this is NOT

- Not pixel-perfect reproduction of the source diagram in refurbish — we redraw, not trace.
- Not an interactive slide editor — diagrams render as embedded PNG on the slide.
- Not a replacement for the predefined chart layouts (`bar-chart`, `funnel`, etc.) — those remain the first choice when they fit; the SVG/Excalidraw escape hatches are for content that doesn't.
