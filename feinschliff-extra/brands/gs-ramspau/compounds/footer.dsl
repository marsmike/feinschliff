# gs-ramspau footer — 3-column mono caps with hairline separator above.
# Center column carries deck-level metadata (date stamp, source, etc).
# Canonical: pad-x 120, bottom 48, height 60, rule 22px above text top.

compound footer(left, center, right):
  rect 120,990 1680x1 fill:fog
  text 120,1010  style:footer maxwidth:560 maxheight:30                 "{{ left }}"
  text 680,1010  style:footer maxwidth:560 maxheight:30 align:center    "{{ center }}"
  text 1240,1010 style:footer maxwidth:560 maxheight:30 align:right     "{{ right }}"
