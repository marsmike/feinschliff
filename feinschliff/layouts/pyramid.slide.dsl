# pyramid — 3 stacked tiers: apex triangle + 2 trapezoids.
# Geometry: center X = 490. Each tier is 180 px tall. Widths step
# 240 → 480 → 720 px (widening 240 px per tier, 120 px per side).
# MSO TRAPEZOID default = narrow at TOP → perfectly stacks under the
# triangle without rotation. adj1 = side_inset / min(w, h).
# Middle:  inset=120, min(480,180)=180  → adj1 = 120/180 = 0.6667
# Base:    inset=120, min(720,180)=180  → adj1 = 120/180 = 0.6667
#
# Slot schema:
#   logo, pgmeta, tracker, action_title — header
#   tiers — array, 3 objects (top→bottom): label, heading, body
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:80 "{{ action_title }}"

# ── Pyramid shapes ────────────────────────────────────────────────────
# Apex: isosceles triangle, narrow at top. Center X=490 → left=370.
shape 370,360  240x180 kind:triangle fill:navy-700

# Middle tier: trapezoid (narrow at top by default), no rotation.
# Box left = 490 - 240 = 250. Top edge = 240 px (matches triangle base).
shape 250,540  480x180 kind:trapezoid adj1:0.6667 fill:accent

# Base tier: trapezoid (narrow at top), no rotation.
# Box left = 490 - 360 = 130. Top edge = 480 px (matches middle base).
shape 130,720  720x180 kind:trapezoid adj1:0.6667 fill:ink

# ── Tier headings centered within each band ───────────────────────────
# Apex text sits in the lower half of the triangle (wider there).
text 370,480  style:body color:off-white align:center maxwidth:240 maxheight:48 "{{ tiers[0].heading }}"
text 250,620  style:body color:ink       align:center maxwidth:480 maxheight:48 "{{ tiers[1].heading }}"
text 130,800  style:body color:off-white align:center maxwidth:720 maxheight:48 "{{ tiers[2].heading }}"

# ── Right column callouts with hairlines ─────────────────────────────
rect 1020,340 800x1 fill:fog
text 1020,360 style:h-idx color:accent maxwidth:760 maxheight:24 "{{ tiers[0].label }}"
text 1020,400 style:body  maxwidth:760 maxheight:80              "{{ tiers[0].body }}"

rect 1020,500 800x1 fill:fog
text 1020,520 style:h-idx color:accent maxwidth:760 maxheight:24 "{{ tiers[1].label }}"
text 1020,560 style:body  maxwidth:760 maxheight:80              "{{ tiers[1].body }}"

rect 1020,660 800x1 fill:fog
text 1020,680 style:h-idx color:accent maxwidth:760 maxheight:24 "{{ tiers[2].label }}"
text 1020,720 style:body  maxwidth:760 maxheight:80              "{{ tiers[2].body }}"

rect 1020,860 800x1 fill:fog

footer left:"{{ footer_left }}" right:"{{ footer_right }}"
