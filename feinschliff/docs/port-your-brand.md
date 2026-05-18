# Port your brand to Feinschliff v2

End-to-end walkthrough for adding a new brand pack. The minimal path
is ~10 minutes for a brand that lives on the toolkit's defaults
(palette swap only); a fully custom brand (bespoke chrome + extra
layouts) is a few hours.

If you already have a v1 brand pack (catalog + frozen `.pptx`
templates), start with [Porting an existing v1 brand pack](#porting-an-existing-v1-brand-pack)
below — it covers the migration path. Otherwise skip ahead to
[1. Scaffold the directory](#1-scaffold-the-directory).

## Porting an existing v1 brand pack

v0.3.0 retired the catalog-driven fill engine. A v1 brand pack
typically shipped:

| v1 artifact                              | v2 fate                                                       |
|------------------------------------------|---------------------------------------------------------------|
| `catalog.json`                           | deleted — slot schema now lives in `.slide.dsl` headers        |
| `templates/pptx/*.pptx`                  | deleted — layouts are toolkit-shared `.slide.dsl` recipes      |
| `build_templates.py`                     | deleted — imperative build steps become DSL compounds          |
| `bake_palette.py`                        | deleted — `tokens.json` is hand-authored DTCG                  |
| `DESIGN.md`                              | kept — frontmatter shape carries forward                       |
| `claude-design/<brand>-2026.html`        | kept — drives `compile-html` skeleton generation               |
| `tokens.json` (if present in v1)         | kept — usually a small reshape; diff against `feinschliff`     |
| `examples/`, `assets/`                   | kept                                                          |

[`brands/gs-ramspau/`][gs-ramspau] is the worked example: an in-place
port whose 906-line `build_templates.py` collapsed into six
`.slide.dsl` files and a handful of brand-specific compounds. The
[v0.3.0 CHANGELOG][changelog] entry lists every v1 module that left
the tree.

### 1. Inventory the v1 inputs

Before deleting anything, list what the brand actually shipped:

```
ls brands/<brand>/
```

Mark each artifact against the table above. Anything outside that list
(brand-specific scripts, custom CLI shims) needs a judgement call:
typically it can be deleted once its responsibility is covered by the
DSL pipeline.

### 2. Produce `tokens.json`

In v1 the palette was baked from `DESIGN.md` by `bake_palette.py`. In
v2 `tokens.json` is hand-authored DTCG and is the source of truth. Two
paths:

- **The brand already has a v1 `tokens.json`.** Diff it against
  [`brands/feinschliff/tokens.json`][feinschliff-tokens]. The v2
  schema requires DTCG-style entries (`{"$value": "#..."}`) inside
  `color`, `font-family`, and `font-size` groups. See
  [`lib/schemas/tokens.schema.json`][tokens-schema] for the full
  contract.
- **No `tokens.json` exists yet.** Translate the `colors:` block from
  `DESIGN.md` frontmatter. A minimal palette override looks like the
  example under [3. Author `tokens.json`](#3-author-tokensjson) below.

### 3. Set `extends:` in `DESIGN.md`

If the v1 brand inherited typography from `feinschliff` (most do),
declare it explicitly in v2:

```yaml
---
version: 1.0
name: My Brand
extends: feinschliff
---
```

This pulls every `font-size`, `font-weight`, and slide token from the
parent — your `tokens.json` then only needs to override the palette
and font families. `brands/gs-ramspau/DESIGN.md` is a working example.

### 4. Generate layout skeletons from the design HTML

If the brand kept its `claude-design/<brand>-2026.html` (it should),
the skeleton generator does the boring half:

```
feinschliff compile-html brands/<brand>/claude-design/<brand>-2026.html \
  -o brands/<brand>/layouts/ \
  --theme <brand>
```

This emits one `.slide.dsl` skeleton per `<section data-slots>` with
the slot schema baked into the docstring. Each skeleton is a starting
point — fill in primitives + compound calls, rendering against the
brand's tokens until the output matches the design HTML.

For layouts the toolkit already ships (`title-orange`, `quote`,
`kpi-grid`, …) the brand inherits the canonical recipe and you can
delete the generated skeleton. Only keep skeletons for layouts the
toolkit does not cover.

### 5. (Optional) Brand-specific compounds

If the v1 brand had bespoke composite slides — like gs-ramspau's
`stundenplan` (school timetable), `termine` (event roster), or
`leitbild` (mission statement) — author them as DSL compound files at
`brands/<brand>/compounds/<name>.dsl`. Layouts at
`brands/<brand>/layouts/` can then call them. See
[`brands/gs-ramspau/compounds/`][gs-ramspau-compounds] for the
pattern.

### 6. Verify

```
feinschliff brand inspect <brand>
feinschliff build brands/<brand>/layouts/<layout>.slide.dsl \
  --content examples/v2/<layout>.yaml \
  -o /tmp/smoke.pptx
```

`brand inspect` should show the new pack with its layout inventory
(inherited + brand-only). The build should open in PowerPoint /
Keynote without complaints. Run `feinschliff verify /tmp/smoke.pptx
--json` for an automated overlap / out-of-bounds check.

### 7. Retire the v1 artifacts

Once a deck round-trips through the v2 pipeline, delete:

```
rm  brands/<brand>/catalog.json
rm -r brands/<brand>/templates/
rm  brands/<brand>/build_templates.py
rm  brands/<brand>/bake_palette.py    # if present
```

Examples, assets, and the `claude-design/` HTML carry over untouched.

[gs-ramspau]: ../brands/gs-ramspau/
[gs-ramspau-compounds]: ../brands/gs-ramspau/compounds/
[changelog]: ../CHANGELOG.md
[feinschliff-tokens]: ../brands/feinschliff/tokens.json
[tokens-schema]: ../lib/schemas/tokens.schema.json

## 1. Scaffold the directory

```
mkdir -p brands/<new>/{compounds,assets}
touch brands/<new>/{tokens.json,DESIGN.md}
```

Discovery (`feinschliff brand list`) picks up the brand as soon as
either `tokens.json` or `DESIGN.md` exists. You can confirm at any
point with:

```
feinschliff brand inspect <new>
```

## 2. Author `DESIGN.md`

The simplest form just sets metadata + extends the parent brand's
tokens:

```yaml
---
version: 1.0
name: My Brand
extends: feinschliff
description: "Quick note on the brand's register, audience, voice."
---

## Overview

(prose about the brand)
```

`extends: feinschliff` brings in every font-size, font-weight, slide
token from the parent. Your `tokens.json` then only overrides palette
+ font families.

## 3. Author `tokens.json`

Minimal palette-only override:

```jsonc
{
  "$schema": "https://schemas.designtokens.org/draft-2/format.json",
  "color": {
    "$type": "color",
    "accent":       { "$value": "#FF5722" },
    "accent-hover": { "$value": "#E64A19" },
    "highlight":    { "$value": "#FFAB91" },
    "ink":          { "$value": "#212121" },
    "black":        { "$value": "#212121" },
    "graphite":     { "$value": "#5D4037" },
    "steel":        { "$value": "#8D6E63" },
    "silver":       { "$value": "#BCAAA4" },
    "fog":          { "$value": "#D7CCC8" },
    "paper":        { "$value": "#FAFAFA" },
    "paper-2":      { "$value": "#EFEBE9" },
    "off-white":    { "$value": "#FAFAFA" },
    "off-white-2":  { "$value": "#D7CCC8" },
    "rule-dark":    { "$value": "#3E2723" },
    "white":        { "$value": "#FFFFFF" }
  },
  "font-family": {
    "$type": "fontFamily",
    "display": { "$value": ["Inter", "Helvetica Neue", "Arial", "sans-serif"] },
    "body":    { "$value": ["Inter", "Helvetica Neue", "Arial", "sans-serif"] },
    "mono":    { "$value": ["JetBrains Mono", "Menlo", "ui-monospace", "monospace"] }
  }
}
```

See [`brand-pack-spec.md`](../references/brand-pack-spec.md) for the
full list of required tokens.

## 4. Author `header` + `footer` compounds

The toolkit layouts call `header` and `footer` compounds that every
brand must provide. Mirror an existing brand for the exact signature.

`brands/<new>/compounds/header.dsl`:

```
compound header(pgmeta):
  text 100,56  style:wordmark color:ink              maxwidth:300 "MY BRAND"
  text 1100,56 style:pgmeta   color:graphite         maxwidth:720 "{{ pgmeta }}" align:right
```

`brands/<new>/compounds/footer.dsl`:

```
compound footer(left, center, right):
  rect 100,990 1720x1 fill:fog
  text 100,1010  style:footer maxwidth:560 maxheight:30                 "{{ left }}"
  text 680,1010  style:footer maxwidth:560 maxheight:30 align:center    "{{ center }}"
  text 1240,1010 style:footer maxwidth:560 maxheight:30 align:right     "{{ right }}"
```

If you intend to use any of the toolkit's dark-bg layouts
(`title-ink`, `chapter-ink`, `key-takeaways`), also ship
`header-dark.dsl` and `footer-dark.dsl` — same signatures, lighter
text colors.

## 5. Smoke-build one slide

```
feinschliff build layouts/quote.slide.dsl \
  --brand <new> \
  --content examples/v2/quote.yaml \
  -o /tmp/<new>-quote.pptx
```

Open it. If the chrome looks right and the layout is themed with your
palette, the basics are in place.

## 6. Optional: brand-specific layouts

If your brand needs visual treatments the toolkit doesn't cover,
author `brands/<new>/layouts/<name>.slide.dsl` files. They get picked
up automatically (`feinschliff brand inspect <new>` shows them under
`brand-only`).

Use [`dsl-grammar.md`](dsl-grammar.md) for the primitive syntax. Lean
on [`compounds.md`](../references/compounds.md) for reusable patterns.

## 7. Optional: bake a claude-design HTML

If you want to author the design visually first and have the v2
skeletons generated for you, write a claude-design HTML (see
`brands/feinschliff/claude-design/feinschliff-2026.html` for the
exemplar). Then:

```
feinschliff compile-html brands/<new>/claude-design/<new>-2026.html \
  -o brands/<new>/layouts/ \
  --theme <new>
```

This writes one `.slide.dsl` skeleton per `<section data-slots>` with
the slot schema baked into the docstring. The skeletons are starting
points — you'll typically refine each against a reference render.

## 8. Build a multi-slide deck end-to-end

Author a `plan.yaml`:

```yaml
brand: <new>
out:   /tmp/<new>-deck.pptx
slides:
  - layout: layouts/title-orange.slide.dsl
    content: { pgmeta: "Demo", eyebrow: "WELCOME", title: "My Brand\nin v2" }
  - layout: layouts/quote.slide.dsl
    content_file: examples/v2/quote.yaml
  - layout: layouts/end.slide.dsl
    content: { pgmeta: "Done", title: "Thanks." }
```

Build + verify:

```
feinschliff deck build plan.yaml
feinschliff verify /tmp/<new>-deck.pptx --json
```

A pass on `verify --json` (no overlap / out-of-bounds defects) and a
visual eyeball is the ship gate.

## Optional: pick an image provider

Most brand ports do not need to think about this. If your slides will
use `picture query:"..."` to resolve images at build time (rather than
pre-bundled `path:`), declare an `$image_provider` in `tokens.json`:

```jsonc
"$image_provider": { "kind": "unsplash", "config": { "access_key": "${env:UNSPLASH_ACCESS_KEY}" } }
```

The toolkit ships `unsplash` as the built-in reference provider; custom
providers live in plugins. See
[`../references/image-providers.md`](../references/image-providers.md)
for the full extension contract.

## Dark-brand variants

If you're authoring a brand with a **dark canvas** (`paper` is a dark
color — e.g. `#1E1E2E`, `#2E3440`), you must override `ink`,
`graphite`, and `steel` to light values. These tokens drive body text,
secondary text, and muted text respectively; leaving them at dark
(inherited) values produces unreadable dark-on-dark slides.

Minimum overrides in `tokens.json`:

```jsonc
"ink":      { "$value": "#E8EAF0" },  // high-contrast body text
"graphite": { "$value": "#9DA3B4" },  // secondary text
"steel":    { "$value": "#6B7280" }   // muted / caption text
```

Adjust the hex values to match your dark palette's contrast ratios.
The WCAG legibility gate (`test_wcag_contrast.py`) requires `ink`-on-`paper`
to clear WCAG AA Large (3.0:1); it will fail if these are left at
dark values.

Also author `header-dark.dsl` and `footer-dark.dsl` compounds — the
toolkit's dark-bg layouts (`title-ink`, `chapter-ink`, `key-takeaways`)
call them directly. See step 4 above for the compound signatures.

## Troubleshooting

- **`KeyError: no color token '<name>'`** — your `tokens.json` is
  missing a required token. Either add it or set `extends:` to inherit.
- **`unknown element 'header'`** — the brand has no `compounds/header.dsl`.
  Add the file.
- **slot literal leaks into the rendered slide** — content YAML is
  missing the slot; check the layout's slot-schema docstring.
- **font renders as default sans (not your custom face)** — soffice
  can't find your fonts. Install them locally and re-render.
