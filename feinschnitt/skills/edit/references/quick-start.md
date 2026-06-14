# Quick Start — edit

## Minimal invocation

```
/edit footage.mp4
```

The skill probes the file, transcribes it, proposes an `edit_plan.json`, lints
it, renders a preview, and stops for approval.

## Typical session

```bash
# 1. Transcribe (one-time; result cached in workdir)
feinschnitt edit transcribe footage.mp4

# 2. Lint the plan before render
feinschnitt edit lint footage.mp4 edit_plan.json

# 3. Preview render (default quality)
feinschnitt edit render footage.mp4 edit_plan.json
# → reports output path, then STOPS

# 4. Final render (only after user approval)
feinschnitt edit render footage.mp4 edit_plan.json --quality final --brand <brand-dir>
```

## Short-form video (portrait, ≤60 s)

- Hook title at `start_sec: 0.0`.
- Follow the density budget in `knowledge/editing-doctrine.md` §2.
- Run the concept pass first (`knowledge/concept-visualization.md`), then fill
  connectives via the template picker.
- One `quote_pull` maximum.
- Captions on; 1–2 emphasis phrases copied verbatim from `words.json`, chosen
  from speaker-only stretches.

## Longform video (landscape or >60 s)

- Skim `words.json` for topic shifts: pauses ≥1.5 s, markers "OK so" / "next up".
- Author chapter-by-chapter into a single `edit_plan.json`.
- ≥1 beat per 60 s; concept quota per chapter (`concept-visualization.md` §5).
- ~1 emphasis phrase/minute; `vertical_timeline` ≤6 steps (lint warns).
- Rolling density cap crosses chapter boundaries.
