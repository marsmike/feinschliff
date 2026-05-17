# Plateau categories — when to redirect vs. accept floor

## Pattern
After 2-3 iterations on the same layout without measurable structural
improvement, the remaining drift is in one of three buckets:

**(a) Position drift** — text/shape is in the wrong place. Solvable by
re-measuring source and updating coordinates. Symptom in the diff mask:
a clear "doubled" outline (source ghost + render ghost separated by 5-30
px). Score moves with each measurement pass.

**(b) Geometry drift** — wrong primitive kind, wrong skew angle, wrong
aspect ratio. Solvable by switching MSO_SHAPE / adjusting `adj1` / using
the right compound. Symptom: the shape is in the right *region* but the
edges/curves don't line up; the diff mask shows a "halo" around the
shape's outline. Each iteration moves the score by 2-5%.

**(c) Font-metric drift** — text is at the right position but renders at
slightly different size, weight, or letter-spacing. NOT solvable without
the brand's actual font. Symptom: every text region in the diff mask
shows a uniform shimmer; positions are correct; iteration produces zero
score change. Floor is typically 8-15% for text-heavy layouts.

## Trigger
- Layout scored X%, you made a position fix, layout now scores X-1% or
  worse. (Position iteration has plateaued OR change actually regressed.)
- Same layout has been iterated on for 2+ rounds with <1% improvement.

## Fix shape
1. **Categorize first.** Open the diff mask. If you see (c)-pattern
   (uniform text shimmer, correct positions), STOP — install the brand
   font or accept the floor.
2. If (a) or (b), **switch categories**. Don't keep tuning positions if
   the geometry is wrong; don't keep swapping primitives if the issue is
   measurement.
3. **Redirection move**: try a structurally different change. Examples:
   - "I've been re-measuring callout positions; let me try the rect's
     SIZE instead, which I assumed was right."
   - "I've been adjusting bar heights; let me try the chart's vertical
     baseline position, which determines all bar offsets."
   - "I've been moving the title; let me try a different `style:` token
     (display vs title vs section).

## For `feinschliff:compile`
Compile should warn at scaffolding time when source has typography
features (custom kerning, alternate glyphs, OpenType features) that the
toolkit's font fallback chain can't reproduce. Make the font-metric
floor visible upfront so brand-pack authors don't burn iterations on
unsolvable text drift.

## Evidence
- agenda: 5 passes through position tuning, plateaued at 22-29%
  structural. Diff mask shows uniform text shimmer with correct
  positions → category (c). Floor accepted.
- styleguide-frames: 4 position passes brought it 30% → 16%. Remaining
  drift is parallelogram edge thickness vs source's 8px-stroke
  thickness — category (b). Single-pixel adjustment may close it.
- cover-orange: 1 position pass + 1 asset swap closed 25% → 3%. No
  plateau because the issue was in different categories per round.
