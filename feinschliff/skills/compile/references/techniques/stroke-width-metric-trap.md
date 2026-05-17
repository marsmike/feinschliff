# Stroke-width metric trap

## Pattern
When source and render have a positional offset on a stroked shape (e.g.
parallelogram outline drawn 3-5 px off from source's position), pixel-
diff metrics can be IMPROVED by making the render's stroke THINNER —
even when source's stroke is visibly thick. Reason: fewer mismatched
edge pixels along an offset stroke means lower diff_ratio. The metric
"improves" while the render gets visually WORSE.

## Trigger
- Working on a layout with stroked geometric shapes.
- Iterating stroke-width and watching `struct_diff_ratio`.
- Each thinning step shows a small score improvement.
- Visual inspection: render now has hair-thin strokes that don't match
  source's chunky 8-10px outlines.

## Fix shape
- **Cross-check visually after every stroke-width change.** Don't trust
  the metric for stroke-width tuning.
- Set stroke-width by direct measurement against source (count pixels
  in the source PNG; the rendered stroke at 1920×1080 design should
  match that count).
- If stroke-width 8 (visually correct) scores worse than stroke-width 2
  (visually wrong), the residual drift is POSITIONAL, not weight. Fix
  positions instead of thinning the stroke.

## For `feinschliff:compile`
Compile-shipped verifier should weight pixel mass differently than pixel
count for stroked shapes. A simple per-shape "expected stroke area"
check (count of orange pixels within the bbox / expected area at the
declared stroke width) is more robust than raw mismatch ratio when
strokes are the main diff signal.

## Evidence
- styleguide-frames stroke-width tuning trace:
  - stroke:8 → struct 15.99%, visually matches source's chunky outlines.
  - stroke:6 → 14.94%
  - stroke:5 → 14.23%
  - stroke:4 → 13.95%
  - stroke:3 → 13.46%
  - stroke:2 → 12.95%, visually WRONG (hairlines, not source's chunky orange).
- Optimum by metric: 2. Optimum visually: 5-8. Final choice: 5 (close to
  source's apparent ~6-8 with slight bias toward the metric's preference).
