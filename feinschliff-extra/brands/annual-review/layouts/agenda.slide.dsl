---
role: agenda
ideal_count: [1, 1]
data_band: none
comparison: false
variety_exempt: true
family: framing
slide_index: 2
slots:
  text_1: {role: title, chars: 54, default: Agenda}
  text_2: {role: body, chars: 935, default: 01. Introduction\n02. Results from last year\n03. Team\n04. What's next\n05. …}
  text_3: {role: footer, chars: 26, default: Annual Review}
  text_4: {role: footer, chars: 84, default: 'September 3, 20XX'}
  text_5: {role: page-number, chars: 11, default: '2'}
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: agenda
canvas 1920x1080
theme annual-review

rect 0,-1 1757x917 fill:highlight
line 163,295 1758,296 stroke:fog stroke-width:12

text 162,157 style:sub color:black weight:bold size:44pt valign:bottom padding:1 maxwidth:1748 maxheight:102 "{{ text_1 | default(\"Agenda\") }}"
text 162,360 style:sub color:black weight:bold size:28pt padding:1 maxwidth:1748 maxheight:621 "{{ text_2 | default(\"01. Introduction\n02. Results from last year\n03. Team\n04. What's next\n05. Closing\") }}"
text 1307,991 style:body-sm color:black size:12pt valign:middle padding:14,7,14,7 maxwidth:231 maxheight:29 "{{ text_3 | default(\"Annual Review\") }}"
text 1548,991 style:body-sm color:black size:12pt padding:1 maxwidth:252 maxheight:79 "{{ text_4 | default(\"September 3, 20XX\") }}"
text 1810,991 style:body-sm color:black size:12pt valign:middle padding:14,7,14,7 maxwidth:100 maxheight:29 "{{ text_5 | default(\"2\") }}"
