# Cover layouts: half-bleed split, not full-bleed

## Pattern
A naïve scaffold from a cover-slide thumbnail sees "lots of orange" and
emits a full-bleed `rect 0,0 1920x1080 fill:accent`. But many corporate
brands actually use **white-left third + colored-right two-thirds** with
the illustration/photo occupying the colored half. The left strip carries
the title + hairline + wordmark.

## Trigger
Brand has multiple cover variants (orange, gray, dark, illustration).
Looking at a single thumbnail you can't tell whether it's a half-bleed
split with content on the right, or a full-bleed canvas. The thumbnail
ratio LOOKS full-bleed.

## Fix shape
Default cover layouts to the split pattern:
```
rect 0,0 640x1080 fill:paper                 # left third
rect 640,0 1280x1080 fill:accent             # right two-thirds
text 75,55 style:wordmark color:ink ...      # wordmark top-left
text 1495,75 style:pgmeta align:right ...    # tag top-right
picture 700,180 1140x720 path:{{ illu }}     # illustration on colored half
rect 75,680 50x4 fill:ink if:{{ title }}     # hairline
text 75,710 style:title color:ink ...        # title bottom-left
```

The full-bleed variant is the exception: ONLY when source has zero
chrome (no wordmark, no tag, no hairline, no title) — that's a divider,
not a cover. Detect by counting text elements in the source thumbnail.

## For `feinschliff:compile`
Compile's cover-layout scaffolder should default to the split pattern.
Only emit a full-bleed when the source thumbnail has fewer than 2 text
regions detected. Cuts a 50%-diff defect from the first render.

## Evidence
- Corporate-brand cover-orange first pass: full-bleed orange → 54%
  structural diff vs source.
- Swap to split pattern → 25% diff. Add extracted illustration → 3%.
- Same fix applied to cover-gray and cover-illustration; each dropped
  from 30%+ to <8% after the structural change alone.
