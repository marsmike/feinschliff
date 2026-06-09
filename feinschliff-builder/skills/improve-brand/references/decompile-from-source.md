# Bootstrap layouts from a source PPTX

`improve-brand` is a polishing loop — it expects layouts to already
exist. When you have a source PPTX deck and want to bootstrap the
brand's `.slide.dsl` files in one shot, use the hybrid decompiler.

## Backends

The toolkit ships two decompilers:

| Backend                          | When to use                                                                                |
| -------------------------------- | ------------------------------------------------------------------------------------------ |
| `lib/dsl/pptx_decompile.py` (default) | Primitive-level reverse mapping. Fast, no external deps. Loses chart geometry and master-inherited chrome. |
| `lib/dsl/pptx_svg_decompile.py` (hybrid) | Combines PPTX XML semantics with optional SVG geometry. Higher fidelity on charts and custGeom. **Use this for brand bootstrap.** |

The hybrid backend is where the higher-fidelity work lives — classifier
improvements, chart geometry extractor, and `cap="all"` detector all
sit on this path.

## Bootstrap workflow

### Option A: single-slide spot-check

```bash
uv run python lib/dsl/pptx_svg_decompile.py \
    path/to/source-deck.pptx \
    --slide 5 \
    --theme <brand> \
    --brand-tokens brands/<brand>/tokens.json \
    --layout-name cover-orange > brands/<brand>/layouts/cover-orange.slide.dsl
```

Useful when you want to redo just one layout, or when you're checking
how the decompiler handles a specific slide before doing a bulk run.

### Option B: bulk decompile via verify-map

This is the path you'll use most often. Requires:
1. `brands/<brand>/tokens.json` — brand palette + style overrides
2. `brands/<brand>/verify-map.yaml` — maps layout names to source slide
   numbers:

   ```yaml
   layouts:
     cover-orange: 5
     timeline-gantt: 22
     table: 52
     # …one entry per layout you want bootstrapped
   ```

3. Source PPTX path

Then:

```bash
uv run python scripts/brand_decompile_all.py \
    --brand-pack brands/<brand> \
    --source-pptx path/to/source-deck.pptx
```

Output: one `<layout>.slide.dsl` per `verify-map.yaml` entry written to
`brands/<brand>/layouts/`. Existing files are snapshotted to
`brands/<brand>/layouts.bak/` first. Use `--dry-run` to preview without
writing; `--only <name> <name>` to restrict to a subset.

### Option C: index-named slide-by-slide (via existing CLI)

```bash
uv run feinschliff-builder decompile path/to/source-deck.pptx \
    --brand <brand> -o brands/<brand>/layouts/ --with-svg
```

Uses the existing `feinschliff-builder decompile` CLI with the new
`--with-svg` flag. Writes `slide-NN.slide.dsl` per slide (numeric
names, not layout-typed). Use this when you don't have a `verify-map.yaml`
yet and just want a starting set of files.

## After bootstrap

```bash
# Measure the first-pass fidelity
uv run python scripts/brand_verify_loop.py \
    --brand-pack brands/<brand> \
    --source-pptx path/to/source-deck.pptx

# Read the report
cat out/<brand>/verify-loop/diff/report.json

# Drive each above-threshold layout through the improve-brand skill
#    — see ../SKILL.md
```

## What the hybrid decompiler does *not* do

- **No asset extraction.** Pictures emit as placeholder slot
  expressions (`picture … path:"{{ image | default:'…' }}" cover:true`).
  If you want extracted images on disk, use the default
  (`lib/dsl/pptx_decompile.py`) which writes `source-slide-NN-K.<ext>`
  next to the layout files.
- **No compound recognition.** Footer-region text emits as N plain
  `text` primitives. If your brand has a `footer(...)` compound,
  manually collapse the lines (or write a brand-specific post-pass).
- **No SVG geometry pass yet from CLI.** The hybrid module reserves
  the SVG cross-check path (`pdf_path` arg on `derive()`), but the
  CLI does not invoke `pdf2svg` automatically. Programmatic callers
  can wire it in; the CLI default is PPTX-only hybrid mode.

## Tuning the classifier

The pt-to-style classifier (`_style_for`) was empirically tuned
against a representative source deck at 1920×1080. Default thresholds:

| Source pt | DSL style |
| --------- | --------- |
| ≥ 60      | `display` |
| 40–59     | `title`   |
| 28–39     | `title-l` |
| 22–27     | `agenda-t`|
| 18–21     | `sub` (or `body` if multi-paragraph) |
| 13–17     | `body`    |
| ≤ 12      | `body-sm` |

If your brand uses materially different font-size tokens than the
feinschliff baseline (e.g. body at 26px instead of 22px), the
classifier may pick a style whose px size doesn't match the source
visual. Fix by overriding the styles in your brand's
`tokens.json` `style: { body: {...}, body-sm: {...} }` block —
the classifier picks tokens by name; tokens.json controls what those
names render as.
