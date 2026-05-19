# improve-brand — detailed workflow

The full loop, end-to-end, with the dispatch shape that makes per-slide
sub-agents efficient.

## 1. Pre-flight

Confirm the brand pack is ready for polishing, not scaffolding:

```bash
test -f brands/<brand>/tokens.json
test -f brands/<brand>/verify-map.yaml
ls   brands/<brand>/layouts/*.slide.dsl | wc -l   # ≥ verify-map entries
```

If `verify-map.yaml` is missing, hand-author one: every layout you want
to verify needs a `<layout-name>: <source-slide-number>` entry. Without
it, the loop has nothing to compare against.

## 2. Baseline run

```bash
uv run python scripts/brand_verify_loop.py \
    --brand-pack brands/<brand> \
    --source-pptx path/to/source-deck.pptx
```

Outputs land under `out/<brand>/verify-loop/`:
- `source-png/slide-NN.png` — one per slide referenced
- `render-png/<layout>.png` — one per layout in `verify-map.yaml`
- `diff/slide-NN_<layout>_overlay.png` — 3-panel diff (source | render | red mask)
- `diff/report.json` — keyed by layout name, each entry has
  `struct_diff_ratio`, `picture_coverage`, `slide`, `picture_slots`,
  `mean_abs_diff`, `total_diff_ratio`, `ssim`
- `diff/score-trace.jsonl` — one row appended per run, used by
  `brand_plateau.py`

## 3. Read the report

```python
import json
report = json.load(open("out/<brand>/verify-loop/diff/report.json"))
work_set = [k for k, v in report.items() if v["struct_diff_ratio"] > 0.05]
```

The work set is the layouts you'll fan out to sub-agents this round.

## 4. Fan out (the important part)

Issue ONE assistant message containing N `Agent` tool calls — one per
layout in the work set. The runtime executes parallel tool calls
concurrently; serial dispatch wastes wall time.

Each `Agent` call receives a prompt rendered from
[`per-slide-prompt.md`](per-slide-prompt.md) with the layout's specific
paths and current metrics filled in.

`subagent_type` choice:
- **`general-purpose`** is the default. Sub-agents need to Read PNGs +
  DSL and Edit one DSL file.
- A future `feinschliff-layout-improver` agent type could ship with
  the toolkit pre-armed with tokens-schema awareness. Not yet
  available.

## 5. Collect results

Each sub-agent returns a one-line summary or "no change made". The
parent does not act on individual sub-agent messages; it just notes
which layouts reported edits.

## 6. Re-render + re-verify

```bash
uv run python scripts/brand_verify_loop.py \
    --brand-pack brands/<brand> \
    --source-pptx path/to/source-deck.pptx \
    --skip-source-export                       # source PNGs unchanged
```

Compare new `report.json` against previous. Use
`scripts/brand_plateau.py` if you have ≥3 runs and want a structured
plateau verdict.

## 7. Plateau handling

After each round, compute `delta = previous_struct_diff - current_struct_diff`
per layout. Classify:

| Δ                  | Verdict      | Action                                                                                            |
| ------------------ | ------------ | ------------------------------------------------------------------------------------------------- |
| `Δ > +0.005`       | improved     | Keep iterating.                                                                                   |
| `−0.005 ≤ Δ ≤ +0.005` | plateau   | Sub-agent has exhausted easy wins. Promote to user or apply a plateau-categories.md technique.   |
| `Δ < −0.005`       | regressed    | Undo via git (user's call) or instruct sub-agent to revert its previous edit and try differently. |

If 2 consecutive rounds plateau for a layout, stop dispatching it.

## 8. Termination

Stop the outer loop when ANY of:
- All layouts ≤ threshold
- `--max-iterations` exhausted
- Every remaining layout has plateaued for ≥ 2 rounds

## Example sub-agent prompt (filled)

```text
You are improving ONE layout in a feinschliff brand pack so its rendered
output matches a source PPTX more closely. You operate on file paths
only — read what you need, don't ask for context.

LAYOUT:                cover-orange
BRAND PACK:            /home/user/work/feinschliff/brands/acme
SOURCE PPTX:           /home/user/decks/acme-master.pptx (slide 5)

DSL FILE (your only edit target):
  /home/user/work/feinschliff/brands/acme/layouts/cover-orange.slide.dsl

BRAND TOKENS (read for token names; only edit with explicit user signoff):
  /home/user/work/feinschliff/brands/acme/tokens.json

EVIDENCE (read these for visual diff context):
  source:  out/acme/verify-loop/source-png/slide-05.png
  render:  out/acme/verify-loop/render-png/cover-orange.png
  overlay: out/acme/verify-loop/diff/slide-05_cover-orange_overlay.png

CURRENT METRICS:
  struct_diff_ratio:   12.3%
  picture_coverage:    65.6%
  target_threshold:    5.0%

YOUR JOB
[...as in per-slide-prompt.md template...]
```

## Extending the sub-agent prompt

If your brand has unusual style constraints (e.g. a parallelogram
clipping mask, mandatory wordmark placement, color rules), append a
**Brand-specific guidance** section to the prompt template before
dispatching. Keep it short — 5–10 bullets at most — and reference
files the sub-agent can read instead of repeating their content:

```text
BRAND-SPECIFIC GUIDANCE
- All chrome lives in compounds/footer.dsl; never inline the page number
  or wordmark — call the compound instead.
- Accent color is at full saturation only for the dominant element per
  slide; secondary use must drop to accent-80 or lower.
- Read brands/acme/DESIGN.md (sections "Type" and "Layout grid") before
  editing typography or position.
```

## What the parent does NOT delegate

- Cross-layout consistency checks (token usage across layouts, style
  drift). Sub-agents see one layout at a time and can't catch this.
- Token or schema changes. If a sub-agent reports "needs a new style
  token", surface it to the user — don't let the sub-agent rewrite
  `tokens.json` autonomously.
- Brand pack restructuring. Sub-agents only edit `.slide.dsl` files.

## Cost notes

- Each sub-agent's context: 3 PNGs (~150–400 KB each) + 1 DSL (~1–3
  KB) + 1 tokens.json read. Typical sub-agent run: 8–15 tool calls.
- A 20-layout brand with all layouts above threshold dispatches 20
  parallel sub-agents per round. Budget accordingly.
- Re-render after each round costs ~5–15 seconds per layout
  (LibreOffice headless + pdftoppm); the diff step is fast (~1–2 s).
