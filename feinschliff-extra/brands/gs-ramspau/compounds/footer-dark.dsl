# gs-ramspau footer — dark-mode variant. 3-column mono caps in off-white
# with a hairline rule above. Mirrors footer.dsl but inverts the palette
# for use on tief/ink slide grounds.

compound footer-dark(left, center, right):
  rect 120,990 1680x1 fill:rule-dark
  text 120,1010  style:footer color:off-white-2 maxwidth:560 maxheight:30                 "{{ left }}"
  text 680,1010  style:footer color:off-white-2 maxwidth:560 maxheight:30 align:center    "{{ center }}"
  text 1240,1010 style:footer color:off-white-2 maxwidth:560 maxheight:30 align:right     "{{ right }}"
