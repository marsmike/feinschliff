# leitbild — 4 values in a 2×2 grid. Each card has a top accent strip
# (wiese), a mono numero, a bold title, and body copy.
#
# Slot schema:
#   pgmeta   string — eyebrow (e.g. "Leitbild")
#   title    string
#   values   array, 4 objects:
#       num    string ≤4 (e.g. "01")
#       title  string ≤40
#       body   string ≤180
# Deck-level: footer_left, footer_right.

canvas 1920x1080
theme gs-ramspau

header pgmeta:"{{ pgmeta }}"

text 120,230 style:title-l color:black maxwidth:1680 maxheight:80 "{{ title }}"

# 4 cards in 2×2. Each 822w × 240h. Layout starts y=380; gap 36 both directions.
# Card 1 (top-left)
rect 120,380   822x240 fill:white
rect 120,380   822x6   fill:accent
text 160,408   style:detail color:graphite maxwidth:742 maxheight:24 "{{ values[0].num }}"
text 160,440   style:col-title color:black maxwidth:742 maxheight:60 "{{ values[0].title }}"
text 160,504   style:body   color:ink      maxwidth:742 maxheight:100 "{{ values[0].body }}"

# Card 2 (top-right)
rect 978,380   822x240 fill:white
rect 978,380   822x6   fill:accent
text 1018,408  style:detail color:graphite maxwidth:742 maxheight:24 "{{ values[1].num }}"
text 1018,440  style:col-title color:black maxwidth:742 maxheight:60 "{{ values[1].title }}"
text 1018,504  style:body   color:ink      maxwidth:742 maxheight:100 "{{ values[1].body }}"

# Card 3 (bottom-left)
rect 120,656   822x240 fill:white
rect 120,656   822x6   fill:accent
text 160,684   style:detail color:graphite maxwidth:742 maxheight:24 "{{ values[2].num }}"
text 160,716   style:col-title color:black maxwidth:742 maxheight:60 "{{ values[2].title }}"
text 160,780   style:body   color:ink      maxwidth:742 maxheight:100 "{{ values[2].body }}"

# Card 4 (bottom-right)
rect 978,656   822x240 fill:white
rect 978,656   822x6   fill:accent
text 1018,684  style:detail color:graphite maxwidth:742 maxheight:24 "{{ values[3].num }}"
text 1018,716  style:col-title color:black maxwidth:742 maxheight:60 "{{ values[3].title }}"
text 1018,780  style:body   color:ink      maxwidth:742 maxheight:100 "{{ values[3].body }}"

footer left:"{{ footer_left }}" center:"{{ footer_center }}" right:"{{ footer_right }}"
