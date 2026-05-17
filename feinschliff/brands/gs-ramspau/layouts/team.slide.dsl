# team — 4 teachers in a row, each with photo placeholder + name + role +
# contact. When no real photo is supplied, the placeholder rect is labelled
# "PORTRÄT" in mono caps (suppressed when a real path lands).
#
# Slot schema:
#   pgmeta   string — eyebrow
#   title    string
#   members  array, 4 objects:
#       name             string
#       role             string (mono caps)
#       contact          string (multi-line allowed)
#       photo            string path, optional
#       photo_placeholder string — "PORTRÄT" or empty to suppress label
# Deck-level: footer_left, footer_center, footer_right.

canvas 1920x1080
theme gs-ramspau

header pgmeta:"{{ pgmeta }}"

text 120,230 style:title-l color:black maxwidth:1680 maxheight:90 "{{ title }}"

# 4 columns at x=120/528/936/1344, width 384 with 24px gap, photo y=360 h=320.
# Each member: placeholder rect → optional PORTRÄT label → real picture
# overlays when path provided → name → role → contact.

# Member 1
rect 120,360  384x320 fill:paper-2 stroke:fog
text 120,508  style:detail color:ink align:center maxwidth:384 maxheight:24 if:"{{ members[0].photo_placeholder }}" "{{ members[0].photo_placeholder }}"
picture 120,360 384x320 path:{{ members[0].photo }} cover:true
text 120,704  style:h-hd  color:black  maxwidth:384 maxheight:60 "{{ members[0].name }}"
text 120,764  style:h-idx color:accent maxwidth:384 maxheight:24 "{{ members[0].role }}"
text 120,796  style:body  color:steel  maxwidth:384 maxheight:100 "{{ members[0].contact }}"

# Member 2
rect 528,360  384x320 fill:paper-2 stroke:fog
text 528,508  style:detail color:ink align:center maxwidth:384 maxheight:24 if:"{{ members[1].photo_placeholder }}" "{{ members[1].photo_placeholder }}"
picture 528,360 384x320 path:{{ members[1].photo }} cover:true
text 528,704  style:h-hd  color:black  maxwidth:384 maxheight:60 "{{ members[1].name }}"
text 528,764  style:h-idx color:accent maxwidth:384 maxheight:24 "{{ members[1].role }}"
text 528,796  style:body  color:steel  maxwidth:384 maxheight:100 "{{ members[1].contact }}"

# Member 3
rect 936,360  384x320 fill:paper-2 stroke:fog
text 936,508  style:detail color:ink align:center maxwidth:384 maxheight:24 if:"{{ members[2].photo_placeholder }}" "{{ members[2].photo_placeholder }}"
picture 936,360 384x320 path:{{ members[2].photo }} cover:true
text 936,704  style:h-hd  color:black  maxwidth:384 maxheight:60 "{{ members[2].name }}"
text 936,764  style:h-idx color:accent maxwidth:384 maxheight:24 "{{ members[2].role }}"
text 936,796  style:body  color:steel  maxwidth:384 maxheight:100 "{{ members[2].contact }}"

# Member 4
rect 1344,360 384x320 fill:paper-2 stroke:fog
text 1344,508 style:detail color:ink align:center maxwidth:384 maxheight:24 if:"{{ members[3].photo_placeholder }}" "{{ members[3].photo_placeholder }}"
picture 1344,360 384x320 path:{{ members[3].photo }} cover:true
text 1344,704 style:h-hd  color:black  maxwidth:384 maxheight:60 "{{ members[3].name }}"
text 1344,764 style:h-idx color:accent maxwidth:384 maxheight:24 "{{ members[3].role }}"
text 1344,796 style:body  color:steel  maxwidth:384 maxheight:100 "{{ members[3].contact }}"

footer left:"{{ footer_left }}" center:"{{ footer_center }}" right:"{{ footer_right }}"
