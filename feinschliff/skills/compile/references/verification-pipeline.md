# Verification pipeline for brand-pack iteration

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

```bash
# 1. Initial bootstrap: extract source assets into the brand pack
python scripts/brand_source_extract.py \
    --brand-pack brands/<brand> \
    --source-dir <source-png-export>

# 2. Wire extracted assets into content YAMLs
#    e.g. content/cover-orange.yaml: illustration: "source-cover-orange-1.png"

# 3. Render the brand pack (existing tooling, e.g. render-all.sh per brand)

# 4. Run the visual diff
python scripts/brand_visual_diff.py \
    --brand-pack brands/<brand> \
    --source-dir <source-png-export> \
    --render-dir out/<brand>/png \
    --output-dir out/<brand>/verify

# 5. Inspect overlay PNGs in out/<brand>/verify/, identify the worst
#    layouts by `struct_diff_ratio` in report.json.

# 6. Edit the DSL/content to fix the worst layout. Re-render. Re-verify.

# 7. After ≥3 verify runs without a layout's score moving:
python scripts/brand_plateau.py \
    --output-dir out/<brand>/verify

#    Plateaued layouts get categorized (clean / fine-tuning / structural /
#    rewrite) — see techniques/plateau-categories.md for what to do next.

# 8. Optional: build a clean side-by-side review PDF (no diff mask) for
#    stakeholder walkthrough.
python scripts/brand_compare_pdf.py \
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
