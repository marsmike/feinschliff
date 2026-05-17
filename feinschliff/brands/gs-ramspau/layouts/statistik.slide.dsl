# statistik — 5 horizontal bars showing where pupils come from. Width is
# proportional to the largest value; one bar can be highlighted with wiese.
#
# Slot schema:
#   pgmeta   string — eyebrow
#   title    string
#   unit     string — right-aligned unit label
#   bars     array, 5 objects:
#       label      string ≤30
#       value      number
#       width      number 0..100  (caller's job to scale to max)
#       highlight  bool, optional
#   caption  string — small explanation under chart
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme gs-ramspau

header pgmeta:"{{ pgmeta }}"

# Title left + unit right.
text 120,230  style:title-l color:black maxwidth:1100 maxheight:80 "{{ title }}"
text 1240,260 style:detail color:graphite maxwidth:560 maxheight:36 align:right "{{ unit }}"

# 5 rows. Track is x=420..1620 (1200 wide). Bar height 28, row 72 stride.
# Row 1 (highlight — wiese)
text 120,436   style:h-hd color:black maxwidth:300 maxheight:40 "{{ bars[0].label }}"
rect 420,442   1200x28 fill:fog
rect 420,442   {{ bars[0].width*12 }}x28 fill:accent
text 1640,436  style:h-hd color:black maxwidth:160 maxheight:40 align:right "{{ bars[0].value }}"

text 120,508   style:h-hd color:black maxwidth:300 maxheight:40 "{{ bars[1].label }}"
rect 420,514   1200x28 fill:fog
rect 420,514   {{ bars[1].width*12 }}x28 fill:black
text 1640,508  style:h-hd color:black maxwidth:160 maxheight:40 align:right "{{ bars[1].value }}"

text 120,580   style:h-hd color:black maxwidth:300 maxheight:40 "{{ bars[2].label }}"
rect 420,586   1200x28 fill:fog
rect 420,586   {{ bars[2].width*12 }}x28 fill:black
text 1640,580  style:h-hd color:black maxwidth:160 maxheight:40 align:right "{{ bars[2].value }}"

text 120,652   style:h-hd color:black maxwidth:300 maxheight:40 "{{ bars[3].label }}"
rect 420,658   1200x28 fill:fog
rect 420,658   {{ bars[3].width*12 }}x28 fill:graphite
text 1640,652  style:h-hd color:black maxwidth:160 maxheight:40 align:right "{{ bars[3].value }}"

text 120,724   style:h-hd color:black maxwidth:300 maxheight:40 "{{ bars[4].label }}"
rect 420,730   1200x28 fill:fog
rect 420,730   {{ bars[4].width*12 }}x28 fill:graphite
text 1640,724  style:h-hd color:black maxwidth:160 maxheight:40 align:right "{{ bars[4].value }}"

# Caption.
text 120,810 style:body color:steel maxwidth:1680 maxheight:60 "{{ caption }}"

footer left:"{{ footer_left }}" center:"{{ footer_center }}" right:"{{ footer_right }}"
