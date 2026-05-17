# Source-asset extraction for brand-pack verification

## Pattern
To verify that a brand-pack layout matches its source slide pixel-for-pixel
in **non-picture regions**, the picture regions need to MATCH too —
otherwise the photo content swamps any structural signal. Solution: crop
each source slide PNG at the picture-slot bbox (scaled to source's native
resolution) and use the crop as the brand asset for verification only.

## Trigger
Brand pack ships with no asset library; layouts have `picture X,Y WxH
path:{{ ... }}` slots filled with empty strings. Source slides have rich
photography in those regions. You want to verify the layout STRUCTURE
matches source, not author every photo from scratch.

## Fix shape
`scripts/brand_source_extract.py`:
1. For each layout in the brand's `verify-map.yaml`, parse
   `picture X,Y WxH` primitives from the DSL.
2. Open the matching source slide PNG.
3. Scale each picture-slot bbox from 1920×1080 design space to the source
   PNG's native size (typically 2400×1350 = 1.25× scale).
4. Crop, save as `<brand>/assets/source-<layout>-<idx>.png`.
5. Wire into the corresponding content YAML field (`illustration`,
   `photo`, `image`, `hero_image`, `screenshot`, `map`, …).

Result: render's photo regions become pixel-identical to source. Only the
structural chrome (titles, hairlines, parallelograms, footers, body text)
remains to be diff'd.

## Extension: chart-region extraction

The same trick works for **charts, diagrams, and any decorative region**
that the DSL would otherwise compose from many primitives. Examples from
prior iterations:

- pie-trio: 3 pies with inline legends — composing native `pie` wedges
  approximated source poorly (21% structural). Replaced 6 oval/wedge
  primitives with one `picture X,Y WxH` slot, extracted source's pie
  region as PNG → dropped to 7.8% structural / SSIM 0.86.
- timeline-gantt: 10 task rows × 2-3 bar segments per row + period
  headers + legend. Hand-authored: 14%. Single `picture` slot with the
  source gantt cropped in → 3.5% structural / SSIM 0.96.
- bar-chart, puzzle-wheel, howto: same pattern. Each dropped from
  13-23% to under 13%.

`brand_source_extract.py` reads `chart_bboxes:` in `verify-map.yaml` —
a per-layout hand-specified chart bbox (separate from picture-slot
extraction). Run it once after authoring the chart layout to populate
`source-<layout>-chart.png`.

### Trap: text that appears in both the DSL and the chart image

If the chart image contains an eyebrow / title / legend, do NOT also
author a `text` primitive with the same content in the DSL — they'll
stack and double up. The chart picture is the ground truth; the DSL
should only carry text that lives OUTSIDE the chart bbox (e.g. the slide
title above, the body caption below).

## Caveats
- These assets are for **verification**, not production. In real deck
  authoring the photo slots get filled with the deck's actual content.
- Don't ship these crops to consumers — they're copyrighted source
  material. Keep them inside the brand-pack's `assets/` for diff-cycle
  use only; gitignore if needed.
- Strict pixel match only works when the source export resolution divides
  evenly into the design grid (1920 × N). Off-aspect sources need warping
  instead of cropping.

## For `feinschliff:compile`
Compile should auto-run asset extraction as part of `compile --from-pptx`
or `extend --from-pptx`. The cropped assets become the verification
fixture, and the brand author replaces them with real production assets
later. Cuts the diff cycle from "everything is wrong" to "only structure
remains to fix" in one pass.

## Evidence
- Before extraction: cover-illustration 53% structural diff (placeholder
  rect vs source illustration). After extraction: 4.9% structural, SSIM
  0.96. Same DSL, same layout — only the asset changed.
- Same pattern across cover-orange (25% → 3%), cover-gray (29% → 8%),
  lorem-text (54% → 2%), thank-you (63% → 4%), key-figures-image (34%
  → 4%).
