# process-flow — 5 chevron stages pointing right; one highlighted as
# active in the brand accent.
#
# Slot schema (data-slots from feinschliff-2026.html · 21):
#   logo, pgmeta, tracker, kicker, action_title — header
#   stages — array, 3–7 objects: counter, heading, body, active? bool
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:160 "{{ action_title }}"

# 5 chevrons, each 360w × 360h at y=480, increment 340 (overlap 20).
# adj1 must be set explicitly: OOXML default is 50000 (=0.5) which produces
# a degenerate zero-body chevron (notch tip meets point base in the middle).
# LibreOffice silently renders something nicer when adj is unspecified, but
# PowerPoint honors the default and the two diverge. adj1=0.15 yields:
#   ss = min(w,h) = 360
#   notch+point inset = 0.15 * 360 = 54 px each
#   body width = 360 - 108 = 252 px  (text maxwidth=240 fits with slack)
# This gives the wider body the chevron needed and renders consistently
# across LibreOffice / PowerPoint / Keynote.
shape 80,480    360x360 kind:chevron adj1:0.15 fill:paper-2 stroke:fog
shape 420,480   360x360 kind:chevron adj1:0.15 fill:paper-2 stroke:fog
shape 760,480   360x360 kind:chevron adj1:0.15 fill:accent
shape 1100,480  360x360 kind:chevron adj1:0.15 fill:paper-2 stroke:fog
shape 1440,480  360x360 kind:chevron adj1:0.15 fill:paper-2 stroke:fog

# Text overlaid in each stage (X shifted right to clear the chevron's pointed tail,
# which insets 54 px at adj1=0.15; body text now starts well inside the body area).
text 140,520   style:h-idx color:accent maxwidth:240 "{{ stages[0].counter }}"
text 140,560   style:h-hd  maxwidth:240 maxheight:60  "{{ stages[0].heading }}"
text 140,650   style:body  maxwidth:240 maxheight:160 "{{ stages[0].body }}"

text 480,520   style:h-idx color:accent maxwidth:240 "{{ stages[1].counter }}"
text 480,560   style:h-hd  maxwidth:240 maxheight:60  "{{ stages[1].heading }}"
text 480,650   style:body  maxwidth:240 maxheight:160 "{{ stages[1].body }}"

text 820,520   style:h-idx color:ink   maxwidth:240 "{{ stages[2].counter }}"
text 820,560   style:h-hd  color:ink   maxwidth:240 maxheight:60  "{{ stages[2].heading }}"
text 820,650   style:body  color:ink   maxwidth:240 maxheight:160 "{{ stages[2].body }}"

text 1160,520  style:h-idx color:accent maxwidth:240 "{{ stages[3].counter }}"
text 1160,560  style:h-hd  maxwidth:240 maxheight:60  "{{ stages[3].heading }}"
text 1160,650  style:body  maxwidth:240 maxheight:160 "{{ stages[3].body }}"

text 1500,520  style:h-idx color:accent maxwidth:240 "{{ stages[4].counter }}"
text 1500,560  style:h-hd  maxwidth:240 maxheight:60  "{{ stages[4].heading }}"
text 1500,650  style:body  maxwidth:240 maxheight:160 "{{ stages[4].body }}"

footer left:"{{ footer_left }}" right:"{{ footer_right }}"
