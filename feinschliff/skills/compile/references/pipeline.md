# /compile pipeline

`/compile` runs `feinschliff compile-html` against a brand's claude-design
HTML and emits one `.slide.dsl` skeleton per `<section data-slots="…">`.
Each skeleton carries:

- a header comment with the slide label, role, when-to-use guidance, and
  the parsed slot schema from `data-slots`;
- a `canvas 1920x1080` declaration and the brand's `theme` directive;
- the standard `header pgmeta:"..."` and `footer left:"..." right:"..."`
  scaffolding;
- a `TODO` marker where the author lays in the actual primitives.

The skill is **per-template** in v2 — one HTML section → one skeleton →
one `.slide.dsl` to hand-author. There is no `catalog.json`, no
`templates/pptx/<id>.pptx`, no placeholder-fill engine; the DSL file IS
the source of truth and gets compiled to PowerPoint by the deck builder.

## Common preconditions

- `<brand-root>` resolves to one of `feinschliff/brands/<brand>/` (see
  [`../SKILL.md`](../SKILL.md#brand-override) for resolution order). All
  paths below are relative to `feinschliff/`.
- The brand has a `DESIGN.md` + `tokens.json` (see
  [`../../../docs/brand-system.md`](../../../docs/brand-system.md)).
- The brand has authored a `claude-design/<brand>-2026.html` containing
  one `<section data-slots=…>` per intended layout.

## Step 1 — Scaffold the skeletons

```bash
feinschliff compile-html brands/<brand>/claude-design/<brand>-2026.html \
  -o brands/<brand>/layouts/ \
  --theme <brand>
```

One section in the HTML → one `<slug>.slide.dsl` file under
`brands/<brand>/layouts/`. Existing files at the same path are
overwritten — author-edited content is lost on re-scaffold, so commit
hand edits before re-running.

The skeleton is intentionally minimal. It declares the slot schema in
header comments and lays in `canvas` + `theme` + `header` + `footer`,
but the body is empty (just a `TODO` marker). The author fills in the
actual primitives.

## Step 2 — Author the primitives

Open each generated `.slide.dsl` and lay in primitives (`rect`, `text`,
`bar`, `excalidraw`, `svg`, compound calls). Cross-reference:

- the HTML section the skeleton came from — for positions, sizes, and
  styling cues;
- the slot schema in the header comment — for the `{{ slot_name }}`
  placeholders the deck builder will fill;
- the toolkit's pre-built layouts under `feinschliff/layouts/` — for
  pattern examples (e.g. how `kpi-grid.slide.dsl` lays out a 4-column
  KPI band).

## Step 3 — Tune against a reference

When the brand has a reference render (an existing `.pptx`, a PNG
export from the design tool, etc.), use `dsl_golden_compare.py` to
phash-compare your layout's render against the reference:

```bash
python scripts/dsl_golden_compare.py \
  brands/<brand>/layouts/<id>.slide.dsl \
  --brand <brand> \
  --content brands/<brand>/examples/<id>.yaml \
  --baseline path/to/reference.pptx
```

The `--baseline` path is whatever you have on hand — a hand-saved
reference, a design-tool export, or a previous brand version's render.
The script renders both via LibreOffice and reports the phash distance
plus a side-by-side PNG.

When no reference exists, render alone (`feinschliff build
<id>.slide.dsl --content <id>.yaml`) and eyeball the output.

## Step 4 — Iterative tuning against a source deck

When the brand was extracted from a finished `.pptx`, use the brand-
source-extract → diff loop:

```bash
python scripts/brand_source_extract.py path/to/source.pptx \
  --brand <brand> --out brands/<brand>/.source/

python scripts/brand_visual_diff.py brands/<brand>/.source/ \
  brands/<brand>/layouts/ --brand <brand>

python scripts/brand_plateau.py <id> --brand <brand>
```

See [`verification-pipeline.md`](verification-pipeline.md) for the full
closed-loop iteration recipe.

## Step 5 — Verify the brand pack

Once the layouts render acceptably, run the full brand-pack verifier:

```bash
feinschliff brand inspect <brand>
```

This lists every `.slide.dsl` the brand resolves, plus any toolkit
layouts inherited via the layout pool. Verify the count matches
expectations and that no skeletons remain unfilled.

## Common postconditions

- `brands/<brand>/layouts/<id>.slide.dsl` exists for every intended
  layout; each parses without error.
- `feinschliff brand inspect <brand>` shows the new layouts.
- Diagnostic renders, source extracts, and visual diffs sit under
  `brands/<brand>/.source/` and `<repo>/.debug/` — both gitignored per
  the [`feinschliff/CLAUDE.md`](../../../CLAUDE.md) discipline.

## Failure modes

- **`compile-html` reports "no <section data-slots=…> found"**. Check
  the HTML has the required `data-slots` attribute on each section.
- **`dsl_golden_compare` exits with non-zero phash**. The layout drifts
  from the reference. Either tune the DSL (positions, fonts, colors)
  or accept the difference if the reference itself is stale.
- **Brand inspect missing a layout**. The brand's `layouts/` does not
  contain a `.slide.dsl` for that id. Re-scaffold or hand-author.

## Determinism

Re-running `compile-html` against the same HTML produces byte-identical
skeleton files. Author edits between runs are NOT preserved — commit
before re-scaffolding, or maintain the layouts entirely by hand once
the skeletons are seeded.
