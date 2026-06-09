---
name: compile
description: Scaffold v2 `.slide.dsl` layout skeletons for a brand pack from its claude-design HTML. Use when adding new layouts.
---

# compile — produce v2 layout skeletons

`/compile` runs `feinschliff-builder compile-html` against a brand's
claude-design HTML and emits one `.slide.dsl` skeleton per
`<section data-slots="…">`. Each skeleton carries the slot schema
plus canvas + theme directives; the author then fills in primitives.

A second pass tunes each layout against reference renders via
`scripts/dsl_golden_compare.py` — see
[`references/pipeline.md`](references/pipeline.md).

Active brand resolves: `--brand <name>` → `FEINSCHLIFF_BRAND` →
default `feinschliff`.

## Quick Start

```bash
# scaffold all layouts for a new brand from its claude-design HTML
feinschliff-builder compile-html brands/<new>/claude-design/<new>-2026.html \
  -o brands/<new>/layouts/ --theme <new>

# tune one layout against any reference .pptx (hand-saved, design-tool export, prior version)
python scripts/dsl_golden_compare.py \
  brands/<new>/layouts/quote.slide.dsl \
  --brand <new> \
  --content brands/<new>/examples/quote.yaml \
  --baseline path/to/reference.pptx
```

See [`references/quick-start.md`](references/quick-start.md) for input
formats and tuning tips.

## References

- [`techniques/INDEX.md`](references/techniques/INDEX.md) — diagnostic patterns accumulated from prior brand-pack iterations (theme-effect bleed, native-shape preference, source-asset extraction, plateau categories, etc.). Read before scaffolding a new brand pack.
- [`verification-pipeline.md`](references/verification-pipeline.md) — closed-loop visual-diff workflow: `brand_source_extract` → render → `brand_visual_diff` → `brand_plateau`. Use to iterate a scaffolded brand pack against its source deck.
- [`../../feinschliff_builder/cli/compile.py`](../../feinschliff_builder/cli/compile.py)
- [`../../scripts/dsl_golden_compare.py`](../../scripts/dsl_golden_compare.py)
- [`../../../feinschliff/docs/brand-pack-contract.md`](../../../feinschliff/docs/brand-pack-contract.md)
