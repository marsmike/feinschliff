# pyramid — 3 stacked tiers: apex triangle + 2 trapezoids. The MSO
# TRAPEZOID type has its narrow edge at the bottom by default; rotated
# 180° they widen toward the bottom (matching the pyramid silhouette).
#
# Slot schema (data-slots from feinschliff-2026.html · 24):
#   logo, pgmeta, tracker, action_title — header
#   tiers — array, 3 objects (top→bottom): label, heading, body
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:80 "{{ action_title }}"

# Apex (triangle), top tier — navy-700. Base 320 wide at y=600.
shape 340,460  320x140 kind:triangle fill:navy-700
# Middle tier (trapezoid rotated 180° → wider at bottom) — accent.
# OOXML TRAPEZOID `adj` = inset-per-side as a fraction of min(w,h). For
# this tier ss = min(440, 140) = 140 and inset_per_side = (440-320)/2 = 60,
# so adj1 = 60/140 ≈ 0.4286. Yields narrow edge = 320 → flush with apex base.
shape 280,600  440x140 kind:trapezoid rotate:180 adj1:0.4286 fill:accent
# Base tier (trapezoid rotated 180°) — ink. Narrow edge 440 wide to
# meet middle's bottom edge: ss = 140, inset = (560-440)/2 = 60,
# adj1 = 60/140 ≈ 0.4286.
shape 220,740  560x140 kind:trapezoid rotate:180 adj1:0.4286 fill:ink

# Tier headings centered on each band (light text where appropriate).
# Apex heading lowered y=510 → y=545: triangle width at that height
# is ~183px (vs ~85px at y=510), so the heading text sits inside the
# triangle outline rather than spilling past the apex tip.
text 340,545  style:body color:off-white align:center maxwidth:320 maxheight:48 "{{ tiers[0].heading }}"
text 280,650  style:body color:ink       align:center maxwidth:440 maxheight:48 "{{ tiers[1].heading }}"
text 220,790  style:body color:off-white align:center maxwidth:560 maxheight:48 "{{ tiers[2].heading }}"

# Right column callouts with hairlines.
rect 1020,440 800x1 fill:fog
text 1020,460 style:h-idx color:accent maxwidth:760 maxheight:24 "{{ tiers[0].label }}"
text 1020,500 style:body  maxwidth:760 maxheight:80              "{{ tiers[0].body }}"

rect 1020,580 800x1 fill:fog
text 1020,600 style:h-idx color:accent maxwidth:760 maxheight:24 "{{ tiers[1].label }}"
text 1020,640 style:body  maxwidth:760 maxheight:80              "{{ tiers[1].body }}"

rect 1020,720 800x1 fill:fog
text 1020,740 style:h-idx color:accent maxwidth:760 maxheight:24 "{{ tiers[2].label }}"
text 1020,780 style:body  maxwidth:760 maxheight:80              "{{ tiers[2].body }}"

rect 1020,860 800x1 fill:fog

footer left:"{{ footer_left }}" right:"{{ footer_right }}"
