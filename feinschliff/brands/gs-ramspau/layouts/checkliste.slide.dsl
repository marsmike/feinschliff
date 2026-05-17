# checkliste — 2 categories of checklist items, each with a wiese kicker,
# a hairline, and 5 items with empty-square checkbox markers. Plus a
# claim-bar lockup ("Bitte beschriften…") between title and lists.
#
# Slot schema:
#   pgmeta   string — eyebrow (e.g. "Einschulung · September 2026")
#   title    string
#   claim    string — italic claim-bar text
#   groups   array, 2 objects:
#       heading string ≤30
#       items   array, 5 strings ≤120
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme gs-ramspau

header pgmeta:"{{ pgmeta }}"

text 120,230 style:title-l color:black maxwidth:1680 maxheight:80 "{{ title }}"

# Claim bar — wiese fill, italic white.
rect 120,320 540x40 fill:accent
text 138,326 style:body color:white maxwidth:504 maxheight:32 "{{ claim }}"

# Group 1 (left column, x=120, width 800).
text 120,420 style:h-idx color:accent maxwidth:800 maxheight:32 "{{ groups[0].heading }}"
rect 120,456 800x1 fill:fog
rect 120,484  20x20 fill:white stroke:black
text 156,480  style:body color:ink maxwidth:644 maxheight:64 "{{ groups[0].items[0] }}"
rect 120,556  20x20 fill:white stroke:black
text 156,552  style:body color:ink maxwidth:644 maxheight:64 "{{ groups[0].items[1] }}"
rect 120,628  20x20 fill:white stroke:black
text 156,624  style:body color:ink maxwidth:644 maxheight:64 "{{ groups[0].items[2] }}"
rect 120,700  20x20 fill:white stroke:black
text 156,696  style:body color:ink maxwidth:644 maxheight:64 "{{ groups[0].items[3] }}"
rect 120,772  20x20 fill:white stroke:black
text 156,768  style:body color:ink maxwidth:644 maxheight:64 "{{ groups[0].items[4] }}"

# Group 2 (right column, x=1000, width 800).
text 1000,420 style:h-idx color:accent maxwidth:800 maxheight:32 "{{ groups[1].heading }}"
rect 1000,456 800x1 fill:fog
rect 1000,484  20x20 fill:white stroke:black
text 1036,480  style:body color:ink maxwidth:644 maxheight:64 "{{ groups[1].items[0] }}"
rect 1000,556  20x20 fill:white stroke:black
text 1036,552  style:body color:ink maxwidth:644 maxheight:64 "{{ groups[1].items[1] }}"
rect 1000,628  20x20 fill:white stroke:black
text 1036,624  style:body color:ink maxwidth:644 maxheight:64 "{{ groups[1].items[2] }}"
rect 1000,700  20x20 fill:white stroke:black
text 1036,696  style:body color:ink maxwidth:644 maxheight:64 "{{ groups[1].items[3] }}"
rect 1000,772  20x20 fill:white stroke:black
text 1036,768  style:body color:ink maxwidth:644 maxheight:64 "{{ groups[1].items[4] }}"

footer left:"{{ footer_left }}" center:"{{ footer_center }}" right:"{{ footer_right }}"
