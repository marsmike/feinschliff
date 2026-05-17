# /deck Quick Start

## Create from a brief

```
/deck "Q1 2026 update for exec team: headcount 62k (+3% YoY), revenue 14 bn EUR (+5.1%), 40 factories across 8 regions, 100% green electricity since 2020. Close with thank you."
```

Expected output: 3–4 slide deck (title + kpi-grid + optional chapter-opener + end) saved to `./out/Q1-2026-update.pptx`. The skill picks file name from the user's wording; if ambiguous, default to `deck.pptx`.

## Polish existing

```
/deck polish rough-draft.pptx
```

Expected: a reflowed version saved to `./out/rough-draft-feinschliff.pptx`. Original untouched.

## Polish with hint

```
/deck polish rough-draft.pptx "make it 5 slides, executive focus"
```

Expected: polished version constrained to 5 slides with executive tone.

## Critique an existing deck

```
/deck critique existing.pptx
```

Expected: `existing-critique.md` + `design_brief.json` next to the source. No build, no changes.

## Gotchas

- **KPI-grid value slot is narrow.** Fractional headline numbers like "8.09" can wrap. Use an integer headline and put the exact figure in the orange delta line.
- **bar-chart and graphical layouts bake bar widths at layout-build time.** Label/value placeholders are editable but proportions lie. Use `kpi-grid` or `action-title` for different data.
- **table layout is 5 rows × 5 cols.** Split beyond 5 into multiple slides.
- **action-title wraps at ~90 chars** before colliding with supporting body (schema says 180 but visual budget is half that).
- **chapter-ink / chapter-orange layouts bake "Chapter 01/02" and "01/06" ornaments.** For >2 chapters, use title-orange/title-ink as chapter openers; carry the "CHAPTER 04 · X" label in the eyebrow.
- **process-flow renders 5 hardcoded chevrons** regardless of steps filled. For 3-step content use `three-column` instead.
