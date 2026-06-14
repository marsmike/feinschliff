---
name: deck
description: Build or polish a brand-compliant PowerPoint deck via the v2 DSL pipeline. Use when the user asks to create a deck, make a presentation, or polish a rough .pptx.
---

# deck — Feinschliff DSL deck builder (v2)

Creates / polishes / critiques presentations via the v2 DSL pipeline.
Brand resolves: `--brand` → `FEINSCHLIFF_BRAND` → `feinschliff`.

**Brand layouts are additive to the toolkit's 50 inherited layouts** (process-flow, excalidraw-diagram, excalidraw-diagram-full, kpi-grid, charts, …). Run `feinschliff-builder brand inspect <brand>` for the full pool before claiming a brand-vs-brief mismatch. See [`references/pipeline.md`](references/pipeline.md) → *Brand layout inventory*.

## Quick Start

```
/deck "Q1 2026 update: 62k employees, +5.1% revenue, 40 factories"
```

See [`references/quick-start.md`](references/quick-start.md) for examples.

## Modes

- **create** — `/deck "brief"` → new deck.
- **plan** — `/deck plan "brief"` → paper draft, no render.
- **polish** — `/deck polish rough.pptx` → `--mode cosmetic` (default) preserves slide count, order, and content verbatim and fixes brand chrome / typography / slot overflow only; `--mode redesign` rebuilds arc, layouts, and titles (existing behavior; `--refurbish-all` / `--no-refurbish` / `--refurbish-default` apply here). Pick via flag or AskUserQuestion. Intake still runs; defaults seed from extracted content.
- **critique** — `/deck critique existing.pptx` → read-only defect analysis.

See [`references/modes.md`](references/modes.md) for mode semantics.

## Pipeline

`ask → intake → commit → ingest → approve → plan → ghost-deck → pick layouts → build → verify → revise`.
Full step-by-step: [`references/pipeline.md`](references/pipeline.md).

**Artifacts (all required):** `deck_brief.yaml` · `commitment.yaml` · `content_plan.json` · `ghost_deck_report.md` · `title_lint_report.md` · `picker_report.json` · `plan.yaml` · `craft_report.md` · `verify_report.md`.

**Picker signals** — `diagram_kind` (`concept`/`chart`) steers diagram picks; `layout_history` applies recency penalties for variety (structural layouts exempt). Arc-aware deck-level picking via `feinschliff deck pick-deck` lifts first/last-slide roles into title-primary / closer and warns on missing required acts from the deck_type arc schema. **Build-time checks**: `diagram-overflow`, `diagram-color-mismatch`, `diagram-text-too-small`, `text-overlap`, `out-of-bounds`. Pass `--strict-craft` for Knaflic rules (no pies, claim chart titles, word-count budgets); `--strict-visual` for PIL post-render metrics (whitespace, balance, collision). Verify also catches filler words, vague-so-what, and bare claims.

**Completion rule.** Before declaring done, confirm all nine artifacts exist and `out/verify_report.md` says `Verdict: clean`. Never declare done without a passing visual verify (pipeline Step 4). When the `feinschliff-builder` plugin is installed, `feinschliff-builder verify` and `feinschliff-builder storyline` gates are also available — but `Verdict: clean` in `verify_report.md` is the universal gate. **Fan-out is the default at ≥10 slides** (opt-out: `--no-fanout`) — authoring + verify run in parallel; `deck log-event` + `deck timing` write/read `timing.jsonl`. See [`references/pipeline.md`](references/pipeline.md) → *Step 2a / Step 4a*.

## References

**Recipe:** [`references/pipeline.md`](references/pipeline.md) · [`references/modes.md`](references/modes.md) · [`references/quick-start.md`](references/quick-start.md) · [`references/iteration-loop.md`](references/iteration-loop.md).

**Theory:** [`references/visual-vocabulary.md`](references/visual-vocabulary.md) · [`references/content-best-practices.md`](references/content-best-practices.md) · [`references/narrative-frames.md`](references/narrative-frames.md) · [`references/audience-calibration.md`](references/audience-calibration.md) · [`references/slide-claim-test.md`](references/slide-claim-test.md) · [`references/anti-patterns.md`](references/anti-patterns.md) · [`references/design-brief-schema.md`](references/design-brief-schema.md) · [`references/speaker-notes.md`](references/speaker-notes.md) · [`references/slide-grammar.md`](references/slide-grammar.md).
