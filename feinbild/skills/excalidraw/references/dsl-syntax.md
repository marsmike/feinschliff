# Excalidraw DSL Syntax

Compact grammar that expands to Excalidraw JSON via `feinbild excalidraw expand`.

## Header

```
canvas <W>x<H>     # required; sets the Excalidraw canvas
theme dark         # optional; flips canvas + labels to dark
```

The standalone CLI always supplies its own canvas via the `canvas <W>x<H>`
line. For oversized, high-resolution output you can declare a large canvas
(e.g. `canvas 6880x2880`) — see **Virtual viewport** below.

## Primitives

| Statement | Syntax |
|---|---|
| Box     | `box <id> <x>,<y> <w>x<h> "<label>" [fill:<color>]` |
| Ellipse | `ellipse <id> <x>,<y> <w>x<h> "<label>" [fill:<color>]` |
| Diamond | `diamond <id> <x>,<y> <w>x<h> "<label>" [fill:<color>]` |
| Dot     | `dot <id> <x>,<y> [fill:<color>]`  — 12px filled marker |
| Line    | `line <id> <x1>,<y1> <x2>,<y2> [dashed] [fill:<color>]` |
| **Zone** | `zone <id> <x>,<y> <w>x<h> "<label>" [fill:<color>] [stroke:<color>] [dashed]` |
| **Lane** | `lane <id> <x>,<y> <w>x<h> "<label>" orient:vertical\|horizontal [fill:<color>]` |
| Arrow   | `arrow <from>[:<port>] -> <to>[:<port>] [flag ...]` |
| Text    | `text <id> <x>,<y> "<content>" [size:<level>] [color:<token>]` |
| Group   | `group <id1> <id2> [<id3>...]`  — shared groupId for selection |

`<color>` is a semantic name (see **Colors** below). Defaults to `primary`
if omitted. `\n` inside a quoted label becomes a real newline.

### Zone and lane

**`zone`** — a named rectangular region rendered behind foreground shapes
(opacity 35%, hachure fill). Use to label an architectural area without
spelling out every component inside it.

```
zone cloud 100,80 2400x600 "Cloud"
zone device 100,720 2400x600 "Device"
```

**`lane`** — a swim-lane rectangle with a label on the leading edge
(top for vertical, left for horizontal). Use for responsibility lanes,
build/runtime planes, or hardware/software splits.

```
lane runtime 100,80 6680x1200 "Runtime" orient:horizontal
lane buildtime 100,1400 6680x1200 "Build / Release" orient:horizontal
```

Both render below foreground shapes regardless of declaration order, so
arrows and boxes drawn afterwards sit on top cleanly.

## Arrow flags

All optional, order-independent. Default behavior (no flags) is straight
edge-to-edge along the center-to-center ray, matching upstream Excalidraw.

| Flag | Purpose |
|---|---|
| `via:x1,y1;x2,y2;...` | Manual waypoints between src and dst |
| `route:straight\|elbow` | `elbow` = 2 computed perp turns; default `straight` |
| `style:solid\|dashed\|dotted` | strokeStyle. When unset, arrows that cross a non-endpoint box are auto-set to `dotted` (visual cue for "passes behind") |
| `color:<token>` | strokeColor; default `ink` |
| `weight:primary\|secondary\|muted` | strokeWidth 2.5 / 2.0 / 1.5 |
| `label:"<text>"` | Label rendered along the polyline (placed perpendicular to the arrow, never on it) |
| `labelpos:above\|below\|left\|right\|mid` | Label offset direction; default `mid` auto-picks above for horizontal-ish arrows, right for vertical-ish |

### Layering

Arrow strokes render **behind** foreground shapes (boxes / ellipses /
diamonds). Combined with the auto-`dotted` style, a long arrow that
passes through intermediate boxes reads as "this connection flows
through here" without overlaying the box labels. Arrow text labels are
layered on top of everything so they remain readable.

### Endpoint ports

Anchor an arrow to a specific side of a node:

```
arrow mcu:right -> linux:left label:"SPI"
arrow ctrl:top  -> watchdog:bottom color:danger label:"fault IRQ"
```

Sides: `left`, `right`, `top`, `bottom`. Combinable with `via:` and
`route:elbow`.

### Routing examples

```
arrow a -> b                                  # default straight
arrow a -> b route:elbow                      # auto 2-segment elbow
arrow a -> b via:600,400;600,800              # manual waypoints
arrow a:right -> b:left via:400,300           # port + waypoint
arrow tg -> tg2 color:danger weight:primary   # fault path emphasis
arrow tg -> agent style:dashed label:"config" # config (not request) edge
```

## Colors

Brand-aware tokens resolved against the active brand's `tokens.json`.
Upstream Excalidraw plugin's semantic names alias onto brand tokens:

| Alias | Resolves to | Use for |
|---|---|---|
| `start`    | `accent`       | warm entry-points, triggers |
| `end`      | `success`      | success exits |
| `warning`  | `warning`      | passthrough |
| `decision` | `status-pending` | conditionals (diamond shapes) |
| `ai`       | `tertiary`       | AI / LLM layers |
| `inactive` | `neutral-soft`   | + auto **dashed stroke** (deprecated / disabled) |
| `error`    | `danger`         | error states |
| `code`     | `ink`            | dark fill for code snippets |
| `data`     | `surface-2`      | raised surface for raw data |

Bare brand tokens also accepted: `primary`, `secondary`, `tertiary`,
`accent`, `ink`, `paper`, `neutral`, `success`, `danger`, `warning`,
`surface`, `surface-2`, etc.

## Text levels (`size:` argument)

| Level    | Size | Role |
|----------|------|------|
| `title`    | 28 | bold heading |
| `subtitle` | 20 | section sub-heading |
| `eyebrow`  | 12 | small tracker / label |
| `body`     | 14 | default paragraph |
| `detail`   | 12 | annotation / caption |
| `mono`     | 13 | monospace (Cascadia / fontFamily 3) |

These are base sizes — when the canvas is larger than 1920px wide
(virtual viewport, see below), default font sizes are scaled by
`canvas_w / 1920` so labels stay legible at the larger render resolution.

## Virtual viewport (large high-resolution canvases)

For a deep architecture diagram, declare a large canvas (e.g.
`canvas 6880x2880`). The body is authored in those coordinates and the
renderer rasterizes at that size, giving 16× the pixel area of a
~1720×720 canvas — room for dense, legible detail.

**Author in the canvas coordinate space.** A box at `200,400 1500x600`
sits 2.9% from the left edge and is 21.8% of canvas width — proportionally
the same as `50,100 375x150` in a 1720×720 canvas. The 16× pixel-area
headroom is the point.

**Use larger base sizes.** Body text at 48-64, titles at 96-128, arrow
labels by default scale with canvas (no manual sizing needed). Stroke
widths also scale.

Always declare the canvas explicitly at the top of the file:

```
canvas 6880x2880
box ...
```

## Comments

Lines starting with `#` are ignored.

A common convention is to put a one-line `diagram_brief` header at the
top of the file:

```
# diagram_brief: audience=embedded-engineers complexity=deep type=mcu-firmware-stack
canvas 6880x2880
zone hw 100,2200 6680x600 "Hardware"
...
```

This is documentation for the human reader and downstream tooling;
no parser enforcement in this tier.

## Rendering

The rendered PNG is produced by `feinbild excalidraw render`, which uses
the **pure-Python rough + cairosvg** backend (clean / `roughness=0`,
~150ms for narrow / ~600ms for large canvases). This backend handles all
normal box/arrow/ellipse/diamond/line/zone/lane diagrams.

There is an **optional** Playwright + real-Excalidraw fallback for
documents containing elements rough doesn't model (`freedraw`, `image`,
`frame`), but **feinbild does not install it by default** — render fails
with "the optional Playwright fallback is not installed" if a document
needs it. In practice, avoid those element types; the rough backend
covers everything the DSL above can express.
