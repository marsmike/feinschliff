---
role: content-columns
ideal_count: [6, 6]
data_band: none
comparison: false
family: organizational
slide_index: 11
slots:
  text_1: {role: title, chars: 54, default: Goals for Q2}
  text_2: {role: body, chars: 82, default: Business priorities}
  text_3: {role: body, chars: 80, default: Added priorities}
  text_4: {role: body, chars: 100, default: Employee opportunities}
  text_5: {role: body, chars: 656, default: Increase customer satisfaction by 2%\nMaintain growth}
  text_6: {role: body, chars: 640, default: Decrease the number of rotations by at least 2\nEnsure the cost of developmen…}
  text_7: {role: body, chars: 624, default: Interns begin\nIndoor rec leagues\nChess tournaments\nBig Game watching party…}
  text_8: {role: footer, chars: 26, default: Annual Review}
  text_9: {role: footer, chars: 84, default: 'September 3, 20XX'}
  text_10: {role: page-number, chars: 11, default: '11'}
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: goals-q2
canvas 1920x1080
theme annual-review

line 163,295 1758,296 stroke:fog stroke-width:12

text 162,157 style:sub color:black weight:bold size:44pt valign:bottom padding:1 maxwidth:1748 maxheight:102 "{{ text_1 | default(\"Goals for Q2\") }}"
text 148,367 style:body color:black weight:bold size:18pt padding:14,7,14,7 maxwidth:545 maxheight:104 "{{ text_2 | default(\"Business priorities\") }}"
text 703,367 style:body color:black weight:bold size:18pt padding:14,7,14,7 maxwidth:536 maxheight:102 "{{ text_3 | default(\"Added priorities\") }}"
text 1249,367 style:body color:black weight:bold size:18pt padding:14,7,14,7 maxwidth:661 maxheight:102 "{{ text_4 | default(\"Employee opportunities\") }}"
text 163,481 style:body color:black size:18pt valign:top padding:1 maxwidth:542 maxheight:589 "{{ text_5 | default(\"Increase customer satisfaction by 2%\nMaintain growth\") }}"
text 715,479 style:body color:black size:18pt valign:top padding:1 maxwidth:541 maxheight:591 "{{ text_6 | default(\"Decrease the number of rotations by at least 2\nEnsure the cost of development stays below budget\") }}"
text 1266,479 style:body color:black size:18pt valign:top padding:1 maxwidth:644 maxheight:502 "{{ text_7 | default(\"Interns begin\nIndoor rec leagues\nChess tournaments\nBig Game watching party\nFood drive\") }}"
text 1307,991 style:body-sm color:black size:12pt valign:middle padding:14,7,14,7 maxwidth:231 maxheight:29 "{{ text_8 | default(\"Annual Review\") }}"
text 1548,991 style:body-sm color:black size:12pt padding:1 maxwidth:252 maxheight:79 "{{ text_9 | default(\"September 3, 20XX\") }}"
text 1810,991 style:body-sm color:black size:12pt valign:middle padding:14,7,14,7 maxwidth:100 maxheight:29 "{{ text_10 | default(\"11\") }}"
