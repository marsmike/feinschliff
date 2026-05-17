# MCK action-title header — shared across slides 16-31.
#
# Three stacked elements at top of slide:
#   tracker         small mono caps, right-aligned (chapter/counter)
#   kicker          mono uppercase ink kicker
#   action_title    56px regular ink (the "so-what" takeaway sentence)

compound mck-head(tracker, kicker, action_title):
  text 100,180 style:tracker    maxwidth:1720 maxheight:24 align:right "{{ tracker }}"
  text 100,220 style:act-kicker maxwidth:1720 maxheight:30             "{{ kicker }}"
  text 100,260 style:act-title  maxwidth:1620 maxheight:180            "{{ action_title }}"
