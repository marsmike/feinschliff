# SVG DSL Reference

Compact grammar that expands to full SVG markup via `feinschmiede.diagrams.svg_expand`.

## Header

```
canvas <W>x<H>
```

The viewBox. Required as the first non-comment line (unless invoked inside
a slide-embed block, where the slot or `virtual:WxH` is the canvas).

## Basic primitives

| Statement | Syntax |
|---|---|
| Rectangle | `rect <id> <x>,<y> <w>x<h> <color>` |
| Circle    | `circle <id> <cx>,<cy> <r> <color>` |
| Line      | `line <id> <x1>,<y1> <x2>,<y2> [<color>] [dashed]` |
| Text      | `text <id> <x>,<y> <level> "<content>"` |
| Bar       | `bar <id> <x>,<y> <w>x<h> <color> [value:"<v>"]` |
| Axis      | `axis <id> horizontal\|vertical <x>,<y> <length> "<labels>"` |
| Legend    | `legend <id> <x>,<y> <color>:"<label>" [<color>:"<label>" ...]` |

`<level>` for text: `title` (22pt) · `subtitle` (16pt) · `body` (14pt) ·
`detail` (12pt) · `value` (13pt).

## Extended primitives (deep diagrams)

These were added for the `svg-infographic-full` layout and richer
infographics. They also work in the narrow `svg-infographic` layout.

### Group

```
group <id> [transform:translate(dx,dy)]
  rect ...
  text ...
endgroup
```

Opens an `<g>` element; close with the **`endgroup`** keyword. `transform`
accepts only `translate(dx,dy)` or `rotate(deg[,cx,cy])` — other transforms
rejected at parse time. Groups can nest.

### Polyline / Polygon / Path

```
polyline <id> <x,y> <x,y> ... [stroke:<token>] [stroke-width:<n>] [dashed]
polygon  <id> <x,y> <x,y> ... [stroke:<token>] [fill:<token>] [stroke-width:<n>]
path     <id> "<d>" [stroke:<token>] [fill:<token>] [stroke-width:<n>] [dashed]
```

- Point lists: 2-64 points. Fewer than 2 raises a DSL parse error.
- `path` `d` is restricted to canonical SVG path commands
  `M m L l H h V v C c S s Q q T t A a Z z` plus digits, whitespace,
  comma, period, minus. Anything else (e.g. `style=`, `<script>`) is
  rejected at parse time.
- Default polyline fill is `none`; default polygon fill is `surface-2`.

### Area (filled trend chart)

```
area <id> <x,y> <x,y> ... baseline:<y> [fill:<token>] [stroke:<token>]
```

Renders as a `<polygon>` closed at `baseline:<y>` so the area between the
trend line and the baseline is filled. Fill opacity 35% by default so the
underlying axes remain readable.

### Stacked bar

```
stacked_bar <id> <x,y> <w>x<h> orient:vertical|horizontal \
                                segments:<v1,token1>;<v2,token2>;...
```

Segment values sum-normalise to fill the bbox. `orient:vertical` stacks
bottom-to-top; `horizontal` stacks left-to-right. Use absolute values or
fractions — both work, output is the same.

### Brace

```
brace <id> from:<x,y> to:<x,y> side:left|right|top|bottom \
            depth:<n> ["<label>"] [stroke:<token>] [stroke-width:<n>]
```

Curly bracket annotation rendered as an SVG path. `side` is the direction
the curls face; `depth` controls how far they bow out. Optional label sits
on the outside of the bracket tip.

### Callout

```
callout <id> anchor:<x,y> at:<x,y> <w>x<h> "<text>" \
              [tail:auto|none] [fill:<token>] [stroke:<token>]
```

A rounded-rect bubble at `at:` with a triangular tail pointing toward
`anchor:`. The tail attaches to the bubble edge nearest the anchor. Pass
`tail:none` for a tail-less labelled box (use `label_box` if that's all you
need — fewer tokens).

### Swatch grid

```
swatch_grid <id> <x,y> cols:<n> \
                  swatches:<token1,label1>;<token2,label2>;... \
                  [cell_w:<n>] [cell_h:<n>]
```

Legend / palette grid. Each entry becomes a small filled square + label.
Defaults: `cols=3`, `cell_w=160`, `cell_h=24` (sized for slide-scale
readability).

### Label box

```
label_box <id> <x,y> <w>x<h> "<text>" [variant:title|subtitle|body|detail] \
                                       [fill:<token>] [stroke:<token>]
```

Rect + centered single-line text in one primitive. Saves a few tokens vs.
the `rect` + `text` pair idiom. Variant controls font size.

## Colors

The DSL uses semantic names only. Literal hex / rgb / hsl rejected. The
17-name vocabulary:

| Group | Names |
|---|---|
| Brand   | `primary`, `secondary`, `tertiary`, `accent` |
| Surface | `paper`, `ink`, `surface`, `surface-2` |
| Severity| `success`, `warning`, `danger` |
| Neutral | `neutral`, `neutral-soft`, `neutral-strong` |
| Status  | `status-on`, `status-off`, `status-pending` |

Each name resolves to a hex via `feinschmiede.diagrams.brand_bridge` against the
active brand's `tokens.json`.

## Virtual viewport (full-slide layouts)

The `svg-infographic-full` layout sets `virtual:6880x2880` on its SVG
block. Author primitives in that 4× space. The renderer rasterizes at
6880×2880; PowerPoint downscales 4× on insert into the 1720×720 slot.
PNGs are ~250-600KB at virtual scale; render ~200ms.

## Comments

Lines starting with `#` are ignored. Common convention: a `diagram_brief`
header at the top of the file documenting audience and complexity.
