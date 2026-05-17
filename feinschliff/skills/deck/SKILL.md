---
name: deck
description: Build or polish a brand-compliant PowerPoint deck via the v2 DSL pipeline. Use when the user asks to create a deck, make a presentation, or polish a rough .pptx.
---

# deck — Feinschliff DSL deck builder (v2)

Creates / polishes / critiques presentations via the v2 DSL pipeline.
Brand resolves: `--brand` → `FEINSCHLIFF_BRAND` → `feinschliff`.

**Brand layouts are additive to the toolkit's 43 inherited layouts** (process-flow, excalidraw-diagram, excalidraw-diagram-full, kpi-grid, charts, …). Run `uv run feinschliff brand inspect <brand>` (from the repo root) for the full pool before claiming a brand-vs-brief mismatch. See [`references/pipeline.md`](references/pipeline.md) → *Brand layout inventory*.

## Quick Start

```
/deck "Q1 2026 update: 62k employees, +5.1% revenue, 40 factories"
```

See [`references/quick-start.md`](references/quick-start.md) for examples.

## Modes

- **create** — `/deck "brief"` → new deck.
- **plan** — `/deck plan "brief"` → paper draft, no render.
- **polish** — `/deck polish rough.pptx` → reflow into v2 layouts. Add `--refurbish-all` to also extract embedded diagrams, rebuild them as brand-aware DSL (`.exc.dsl`/`.svg.dsl`), and substitute back into the rebuilt deck. Use `--no-refurbish` / `--refurbish-default` to control per-run.
- **critique** — `/deck critique existing.pptx` → read-only defect analysis.

See [`references/modes.md`](references/modes.md) for mode semantics.

## Pipeline

`ask → ingest → approve → plan → pick layouts → build → verify → revise`.
Full step-by-step: [`references/pipeline.md`](references/pipeline.md).

**Picker signals** — `diagram_kind` (`concept`/`chart`) steers diagram picks; `layout_history` applies recency penalties for variety (structural layouts exempt). **Build-time checks**: `diagram-overflow`, `diagram-color-mismatch`, `diagram-text-too-small`, `text-overlap`, `out-of-bounds`. Verify also catches filler words, vague-so-what, and bare claims.

**Completion rule.** Never declare done without a passing `feinschliff verify --json` → `out/verify_report.json`. **Parallel mode** (≥10 slides) fans out authoring + verify after storyline; `deck log-event` + `deck timing` write/read `timing.jsonl`. See [`references/pipeline.md`](references/pipeline.md) → *Step 2a / Step 4a*.

## References

**Recipe:** [`references/pipeline.md`](references/pipeline.md) · [`references/modes.md`](references/modes.md) · [`references/quick-start.md`](references/quick-start.md) · [`references/iteration-loop.md`](references/iteration-loop.md).

**Theory:** [`references/visual-vocabulary.md`](references/visual-vocabulary.md) · [`references/content-best-practices.md`](references/content-best-practices.md) · [`references/narrative-frames.md`](references/narrative-frames.md) · [`references/audience-calibration.md`](references/audience-calibration.md) · [`references/slide-claim-test.md`](references/slide-claim-test.md) · [`references/anti-patterns.md`](references/anti-patterns.md) · [`references/design-brief-schema.md`](references/design-brief-schema.md) · [`references/speaker-notes.md`](references/speaker-notes.md).
