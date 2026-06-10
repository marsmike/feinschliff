# Verification pipeline for brand-pack iteration

> **Orchestrator shortcut.** `scripts/brand_verify_loop.py` chains
> source-PNG export → render → diff in one command — see
> [the orchestrator section](#orchestrator-brand_verify_looppy) below.
> For an LLM-driven improvement loop that fans out one sub-agent per
> layout, use the [`improve-brand`](../../improve-brand/SKILL.md)
> skill.

Three companion scripts in `scripts/` form a closed-loop verification
cycle that drives brand-pack iteration:

```
                  ┌────────────────────────┐
                  │ render layouts         │
                  │ (existing tooling)     │
                  └──────────┬─────────────┘
                             │ <layout>.png
                             ▼
       ┌────────────────────────────────────────┐
       │ brand_visual_diff.py                   │
       │  • masks picture slots                 │
       │  • computes struct_diff_ratio + SSIM   │
       │  • writes overlay/mask PNGs            │
       │  • appends score to score-trace.jsonl  │
       └──────────┬─────────────────────────────┘
                  │
                  ├─► report.json + per-slide overlays
                  ▼
       ┌────────────────────────────────────────┐
       │ brand_plateau.py                       │
       │  • flags layouts with no movement      │
       │  • routes to plateau-categories.md     │
       └────────────────────────────────────────┘

       ┌────────────────────────────────────────┐
       │ brand_compare_pdf.py    (optional)     │
       │  • side-by-side source vs. render      │
       │  • clean visual review PDF, no diff    │
       │    mask — for stakeholder walkthrough  │
       └────────────────────────────────────────┘
```

Plus a one-off bootstrap for the first run:

```
       ┌────────────────────────────────────────┐
       │ brand_source_extract.py                │
       │  • crops source slides at each         │
       │    picture-slot bbox + chart bbox      │
       │  • saves to <brand>/assets/source-*    │
       └────────────────────────────────────────┘
```

## verify-map.yaml

The pipeline is driven by a single config file at the brand-pack root:

```yaml
# brands/<brand>/verify-map.yaml
layouts:
  cover-orange: 5            # layout name → source slide number
  cover-dark: 1
  pie-trio: 11
  timeline-gantt: 22
  table: 52
  # …one entry per layout you want verified

chart_bboxes:                # optional — for chart/diagram regions that
  pie-trio: [75, 195, 1770, 410]    # aren't covered by picture-slot extraction
  timeline-gantt: [55, 165, 1810, 660]
  bar-chart: [75, 195, 1770, 510]
  # bbox is [x, y, w, h] in 1920×1080 design space
```

## Workflow

These scripts live under `${CLAUDE_PLUGIN_ROOT}/scripts/` and require a dev
checkout (clone + `uv sync`) for their numpy/scikit-image scoring dependencies.

```bash
# 1. Initial bootstrap: extract source assets into the brand pack
python ${CLAUDE_PLUGIN_ROOT}/scripts/brand_source_extract.py \
    --brand-pack brands/<brand> \
    --source-dir <source-png-export>

# 2. Wire extracted assets into content YAMLs
#    e.g. content/cover-orange.yaml: illustration: "source-cover-orange-1.png"

# 3. Render the brand pack (existing tooling, e.g. render-all.sh per brand)

# 4. Run the visual diff
python ${CLAUDE_PLUGIN_ROOT}/scripts/brand_visual_diff.py \
    --brand-pack brands/<brand> \
    --source-dir <source-png-export> \
    --render-dir out/<brand>/png \
    --output-dir out/<brand>/verify

# 5. Inspect overlay PNGs in out/<brand>/verify/, identify the worst
#    layouts by `struct_diff_ratio` in report.json.

# 6. Edit the DSL/content to fix the worst layout. Re-render. Re-verify.

# 7. After ≥3 verify runs without a layout's score moving:
python ${CLAUDE_PLUGIN_ROOT}/scripts/brand_plateau.py \
    --output-dir out/<brand>/verify

#    Plateaued layouts get categorized (clean / fine-tuning / structural /
#    rewrite) — see techniques/plateau-categories.md for what to do next.

# 8. Optional: build a clean side-by-side review PDF (no diff mask) for
#    stakeholder walkthrough.
python ${CLAUDE_PLUGIN_ROOT}/scripts/brand_compare_pdf.py \
    --brand-pack brands/<brand> \
    --source-dir <source-png-export> \
    --render-dir out/<brand>/png \
    --output-dir out/<brand>/compare
```

## What the metrics mean

- **`total_diff_ratio`**: fraction of pixels where source and render
  differ by more than 30/255 in any channel. Compared to whole canvas;
  unmasked.
- **`struct_diff_ratio`**: same fraction, but with picture-slot regions
  zeroed out before counting. The structural signal — measures how well
  the *layout chrome* matches source independent of the photo content.
- **`ssim`**: scikit-image structural similarity, 0..1 (higher better).
  Robust to small position shifts; useful sanity check.
- **`picture_coverage`**: fraction of canvas covered by picture slots.
  When this exceeds ~50%, `struct_diff_ratio` becomes unreliable
  (see techniques/structural-metric-coverage-bias.md).

## Related techniques
- [picture-slot-mask-verifier](techniques/picture-slot-mask-verifier.md)
- [source-asset-extraction](techniques/source-asset-extraction.md)
- [plateau-categories](techniques/plateau-categories.md)
- [structural-metric-coverage-bias](techniques/structural-metric-coverage-bias.md)

## Orchestrator: `brand_verify_loop.py`

`scripts/brand_verify_loop.py` chains source-PNG export → render →
diff into one command, with mtime-keyed caching so re-runs after a
single DSL edit only rebuild the affected layout. Drop-in usage:

```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/brand_verify_loop.py \
    --brand-pack brands/<brand> \
    --source-pptx path/to/source-deck.pptx

# Restrict the set + reuse cached source PNGs
python ${CLAUDE_PLUGIN_ROOT}/scripts/brand_verify_loop.py \
    --brand-pack brands/<brand> \
    --source-pptx path/to/source-deck.pptx \
    --only quote table cover-orange \
    --skip-source-export
```

Defaults to `out/<brand>/verify-loop/` for `source-png/`, `render-png/`,
`diff/`. The diff step delegates to `brand_visual_diff.py`, so the
same `report.json` + `score-trace.jsonl` artefacts are produced — and
`brand_plateau.py` still works downstream.

**Scoring change (Unreleased):** `brand_visual_diff.py` now always
masks picture-slot regions when computing `struct_diff_ratio`, even
when picture coverage exceeds 90%. The previous fall-back to
`total_diff_ratio` for picture-heavy layouts hid meaningful chrome
diffs. `picture_coverage` is still reported so coverage-bias remains
visible — see
[`techniques/structural-metric-coverage-bias.md`](techniques/structural-metric-coverage-bias.md).

## LLM loop: the `improve-brand` skill

For a closed-loop LLM-driven polishing flow, see the
[`improve-brand`](../../improve-brand/SKILL.md) skill. It wraps
`brand_verify_loop.py` and fans out **one sub-agent per layout** in
parallel — each sub-agent reads the per-slide overlay + current DSL
and edits only its assigned layout. The skill handles plateau
detection and iteration budgeting; the user controls all git
operations.
