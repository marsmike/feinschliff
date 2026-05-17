# Verifier MUST mask picture slots

## Pattern
A pixel-diff verifier without picture-slot masking is **misleading**: it
penalizes structural improvements that "fill" a placeholder with content
that differs from source's content. Worst case: an empty `paper-2`
placeholder rect matches source's white background better than ANY real
photo at the same position. The verifier reports a higher score for the
incomplete render.

## Trigger
Layout has a `picture X,Y WxH` slot. Source has a real photo or
illustration there. You replace the empty placeholder with any image →
pixel-diff goes UP, not down. You start to think the change made things
worse.

## Fix shape
Parse `picture X,Y WxH` boxes from each layout DSL. Build a binary mask
over the 1920×1080 canvas; zero those regions in the per-pixel diff array
before computing the structural metric. Report both `total_diff_ratio`
(unmasked) and `struct_diff_ratio` (masked) so you can see when picture
content is dominating vs when structure is the issue.

Edge case: if picture slots cover >90% of canvas (full-bleed photo
layouts like `end`, `thank-you`), masking would zero everything → fall
back to the total diff. Otherwise you get `struct_diff_ratio = 100%`
from a divide-by-tiny-residual.

## For `feinschliff:compile`
The compile skill should ship a verifier with the brand pack. The
verifier MUST distinguish structural defects from picture-content defects.
Pixel-perfect picture match is only possible during the asset-extraction
phase of brand-pack authoring; in production every deck swaps in unique
photos. The structural-only score is the durable signal.

## Evidence
- Before masking: agenda dropped picture, diff went 46% → 45.8% (almost
  zero). Misleading — the layout WAS now correct but content swap masked
  the win.
- After masking + source extraction: cover-orange dropped 25% → 2.9%
  structural, SSIM 0.96. The number now reflects layout fidelity, not
  asset coincidence.
