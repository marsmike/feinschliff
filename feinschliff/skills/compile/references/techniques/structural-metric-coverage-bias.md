# Structural metric bias when picture coverage is high

## Pattern
The masked structural diff (`struct_diff_ratio`) treats every unmasked
pixel equally and divides by the unmasked count. When picture slots
cover >50% of the canvas, the unmasked region is small — and any minor
drift in that residual region produces an inflated ratio.

Concrete: `graphic-image` has a 850×530 chart slot (~22% of canvas) +
a 537×756 photo slot (~20% of canvas) + a 587×493 parallelogram region
that's also masked-adjacent. Total picture coverage ~45%. The remaining
~55% is mostly empty white space, with the structural defects (title
position drift, parallelogram stroke width) concentrated in a tiny
fraction of pixels. Score reads 48% structural ratio even though the
slide is visually 90%+ correct (SSIM 0.85, total diff 30%).

## Trigger
- Layout has multiple large picture slots.
- `struct_diff_ratio` reports >25% but `total_diff_ratio` and SSIM say
  the slide is close.
- Visual inspection confirms the render matches source closely; only
  small text/chrome positions are slightly off.

## Fix shape
- **Cross-check with SSIM and total_diff_ratio.** If SSIM ≥ 0.85 and
  total diff ≤ 15%, the structural score is misleading; the layout is
  near-clean.
- Optional (verifier upgrade): report `struct_diff_pixels` (raw count of
  differing unmasked pixels) alongside the ratio. Absolute pixel count
  is invariant to coverage; ratio is not. Use the count to flag actual
  defects.
- Don't chase the ratio below ~20% on picture-heavy layouts. The
  remaining drift is amortised away in production decks once the chart
  picture is replaced with the deck's actual content.

## For `feinschliff:compile`
Compile-shipped verifier should display all three numbers per layout:
`total_diff_ratio`, `struct_diff_ratio`, `struct_diff_pixels`. If
picture coverage > 50%, prefer `struct_diff_pixels` for ranking. This
matches what a designer reviewing a thumbnail would care about: "is the
chrome at the right pixel positions, regardless of how big the photo
slot is."

## Evidence
- graphic-image: total 30%, structural 48%, SSIM 0.85, visual = clean
  bar chart + photo + parallelogram. Score discrepancy from coverage
  bias.
- thank-you: similar — total 4.4%, structural 5.6%, SSIM 0.94. Same
  pattern but smaller picture (~50% coverage), bias less severe.
- end: total 6.6%, structural 6.6% (no picture mask because coverage
  >90% triggers the all-or-nothing fallback). Cleanest case for
  comparison.
