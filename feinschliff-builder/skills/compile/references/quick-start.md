# /compile quick start

## Scaffold a brand's layouts

```bash
feinschliff compile-html brands/<brand>/claude-design/<brand>-2026.html \
  -o brands/<brand>/layouts/ \
  --theme <brand>
```

One `<section data-slots="…">` in the HTML → one `.slide.dsl` skeleton
under `brands/<brand>/layouts/`. Existing files at the same path are
overwritten — commit author edits before re-scaffolding.

Each skeleton has:

- the slot schema as a header comment (from `data-slots`),
- `canvas 1920x1080` + the brand's `theme` directive,
- standard `header` + `footer` scaffolding,
- an empty body with a `TODO` marker for the author to fill in.

## Tune a single layout against a reference

```bash
python scripts/dsl_golden_compare.py \
  brands/<brand>/layouts/quote.slide.dsl \
  --brand <brand> \
  --content brands/<brand>/examples/quote.yaml \
  --baseline path/to/reference.pptx
```

`--baseline` accepts any `.pptx` — a hand-saved reference, an export
from the design tool, a previous brand version's render. The script
renders both via LibreOffice + phash-compares and emits a side-by-side
PNG. Tighten with `--threshold 4` for kit-template precision; relax
with `--threshold 16` when reference fidelity is approximate.

## Render a layout alone

```bash
feinschliff build brands/<brand>/layouts/quote.slide.dsl \
  --content brands/<brand>/examples/quote.yaml \
  --brand <brand>
```

Useful for brand-new layouts where no baseline exists. Eyeball the
output, iterate the DSL, re-render.

## Inspect the brand's layout pool

```bash
feinschliff brand inspect <brand>
```

Lists every layout the brand resolves, including toolkit layouts
inherited via the shared pool under `feinschliff/layouts/`.

## When `compile-html` runs

Use it when the brand's claude-design HTML changes — a new section
appears, a slot schema is revised, the brand designer hands over an
updated spec. Don't re-run for small layout tweaks; just edit the
existing `.slide.dsl` by hand.
