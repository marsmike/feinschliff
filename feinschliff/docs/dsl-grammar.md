# Feinschliff DSL grammar

A `.slide.dsl` file declares one slide. A `.dsl` file under `compounds/`
declares one or more compounds. Both share the same line-oriented
syntax.

## Top-level structure

```
canvas WIDTHxHEIGHT          # required once per slide (e.g. 1920x1080)
theme NAME                   # advisory; the actual theme comes from the brand pack
…primitive and compound calls (one per line)…
```

Lines starting with `#` are comments. Blank lines are ignored. Each
non-comment line is one node — either a primitive emission or a
compound call.

## Primitives

All primitives share these conventions:
- positional args come first, then `key:value` keyword args
- the **last** token of a `text` line may be a quoted string label
- `X,Y` is a top-left in design pixels (1920×1080 canvas baseline)
- `WxH` is a width × height pair
- `if:VALUE` suppresses emission when `VALUE` is empty or `false`

### `text X,Y "label" style:S color:T align:A maxwidth:W maxheight:H autoshrink:true lang:LOCALE rotate:N`

Renders one textbox. `style` resolves through the brand's style bundles
(see [`tokens.py`](../lib/dsl/tokens.py) — display, huge, title, sub,
body, eyebrow, footer, pgmeta, h-idx, h-hd, h-li, lede, act-title,
act-kicker, tracker, quote, quote-attr, kpi-value, kpi-unit, kpi-key,
kpi-delta, agenda-num, agenda-t, agenda-d, btn, chip, wordmark,
detail, col-num, col-title, col-title-q, col-body, rule, brand-mark,
title-l, display, display-xl, bignum). `color:TOKEN` overrides the
style's default color. `align:` is `left | center | right`.

Multi-line labels use `\n` inside the quoted string (escaped at parse
time). Line spacing uses the style's `line_height`; inter-paragraph
gap is zero.

`autoshrink:true` shrinks the font size down to a 10pt floor until the
label fits the `maxwidth × maxheight` box. Off by default. `lang:LOCALE`
(any pyphen locale, e.g. `de_DE`) inserts U+00AD soft hyphens into the
label before emission so python-pptx can break long compounds at
syllable boundaries; hyphenation is applied before autoshrink so the
shrunk size accounts for hyphenated text. `rotate:N` rotates the text
frame clockwise by `N` degrees (integer). Useful for axis labels, rotated
callouts, and vertical annotation tracks; the bounding box (`X,Y WxH`)
remains in the un-rotated coordinate system. All four opts-in — omit for
byte-identical output.

### `rect X,Y WxH fill:T stroke:T stroke-width:N`

Renders a rectangle. Either side may be omitted (no fill / no stroke).

### `shape X,Y WxH kind:K fill:T stroke:T rotate:DEG fill-opacity:0..1`

Renders a non-rectangular shape. `kind` ∈ `oval | ellipse | circle |
triangle | triangle-down | triangle-left | triangle-right |
right-triangle | chevron | right-arrow | left-arrow | diamond |
trapezoid | rect`. `rotate` is clockwise degrees. `fill-opacity` sets
alpha on a solid fill (OOXML `a:alpha`).

### `line X1,Y1 X2,Y2 stroke:T stroke-width:N`

Renders a connector line between two points.

### `polyline X1,Y1 X2,Y2 [X3,Y3 …] stroke:T stroke-width:N`

Renders a multi-segment open polyline through an ordered sequence of
points. Unlike `line`, which accepts exactly two endpoints, `polyline`
accepts three or more coordinate pairs — useful for step-charts, arrow
traces, or any path that bends. Coordinates follow the same `X,Y`
convention as all other primitives. The polyline is not closed
(first and last points are not connected). No fill is applied.

### `picture X,Y WxH path:P slot:N cover:true`

Renders an image. `path` is brand-asset-relative (e.g. `gem.png`) or
absolute. `slot:N` is a slot lookup. `cover:true` covers the bounding
box (default is contain). When neither resolves to an existing file,
emits a placeholder rect so the slot is visible.

### Reserved no-ops

`canvas` and `theme` are parsed at the top of each slide and consumed
by the emitter setup — they produce no shapes.

## Slot interpolation

Any string value (positional, kw_arg, or label) may include
`{{ EXPR }}` placeholders. The expander resolves them against the
content YAML (for top-level layouts) or against the call's bindings
(for compound bodies).

Expression forms:

| form | example | resolves to |
|---|---|---|
| key | `{{ title }}` | `ctx["title"]` |
| dotted path | `{{ columns[0].counter }}` | walks dict/list |
| arithmetic | `{{ y+h-1 }}` | mixed names + literals + `+ - * /` |
| missing key | unchanged | placeholder stays as-is for debugging |

Arithmetic resolves to an integer when the result lands on a whole
number, otherwise to a short decimal. Use it inside coordinate args
to compute relative positions in compound bodies.

## Escape sequences inside quoted strings

| sequence | result |
|---|---|
| `\"` | `"` |
| `\n` | newline |
| `\t` | tab |
| `\\` | `\` |

## Block constructs

### `for VAR in ITER:` loop

Repeat a block of primitives or compound calls over a list value from
the content YAML:

```
for item in items:
  text {{ item.x }},{{ item.y }} style:body "{{ item.label }}"
  rect {{ item.x }},{{ item.y+30 }} {{ item.w }}x4 fill:accent
```

Rules:
- `ITER` must be a key that resolves to a list in the current content map.
- `VAR` is bound to each element in turn; `{{ VAR.field }}` and
  `{{ VAR[0] }}` paths work inside the body.
- The body is indented (same as a compound body).
- `for` loops may call compounds and nest `if:` guards, but may not
  contain nested `for` loops.
- Loop iteration count is capped at 64 to prevent runaway expansion.

## Compound definitions

```
compound NAME(param1, param2, …):
  text 0,0 style:body "{{ param1 }}"
  rect 0,40 100x4 fill:accent
  …
```

The body is one or more indented primitive or compound-call lines.
Indentation is significant. Parameters are bound by position or by
keyword at the call site; unbound parameters default to empty string.

## Compound calls

```
NAME pos1 pos2 kw1:v1 kw2:v2 …
```

Positional args fill parameters in declaration order; keyword args
override positional. Compounds may call other compounds; recursion
depth is bounded (default 8).

## Resolution order

1. The layout's local nodes are parsed.
2. Slot interpolation runs over each node's pos_args, kw_args, and label.
3. Compound calls expand recursively, with each level's bindings
   substituted into the body.
4. After all compounds are expanded, only primitives remain — these
   reach the emitter.

The emitter loads compounds from two directories in order:
toolkit-standard (`feinschliff/compounds/`) and brand-specific
(`feinschliff/brands/<brand>/compounds/`), with the brand-specific set
overriding on name collision.

### `svg_wireframe` and `if:` guards

`svg_wireframe` (the development-preview renderer that draws bounding
boxes without rendering real content) honours `if:` guards: nodes with
an `if:` kwarg that resolves to empty/false are suppressed from the
wireframe output, matching the emitter's behaviour. This means wireframe
previews accurately reflect conditional slots — a slot that would be
absent in the real render is also absent in the wireframe.

## Diagram block primitives (Phase: diagrams integration)

Embed brand-aware diagrams inside any slide layout. Two block-bearing primitives:

```
svg        <id>  <x>,<y>  <w>x<h>  [from:"<path>"]  { <inline body> }
excalidraw <id>  <x>,<y>  <w>x<h>  [from:"<path>"]  { <inline body> }
```

- `<id>` — required.
- `<x>,<y>` `<w>x<h>` — slide-coordinate region. The region IS the diagram canvas.
- `from:"<path>"` — optional external file. Path is relative to the layout's directory. Mutually exclusive with `{ ... }`.
- The body opens with `{` on the header line; inline DSL must start on a subsequent line.

### Lints

- No inner `canvas` declaration (the region defines it).
- No nested diagrams.
- Empty inline body is an error.

See [docs/diagrams.md](diagrams.md) for the diagram DSL grammars.
