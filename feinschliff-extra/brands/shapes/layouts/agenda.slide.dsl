---
role: agenda
ideal_count: [1, 1]
data_band: none
comparison: false
variety_exempt: true
family: framing
slide_index: 2
slots:
  text_1: {role: body, chars: 1008, default: Introduction\nBuilding confidence\nEngaging the audience\nVisual aids\nFinal
      …}
  text_2: {role: title, chars: 200, default: Agenda}
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: agenda
canvas 1920x1080
theme shapes

shape 77,176 728x728 kind:oval fill:theme-accent2
shape 143,753 86x86 kind:oval fill:theme-accent5

text 914,87 style:body color:black size:24pt autoshrink:true valign:middle padding:14,7,14,7 maxwidth:996 maxheight:908 "{{ text_1 | default(\"Introduction\nBuilding confidence\nEngaging the audience\nVisual aids\nFinal tips & takeaways\") }}"
text 96,176 style:sub color:paper size:44pt autoshrink:true valign:middle padding:14,7,14,7 maxwidth:808 maxheight:728 "{{ text_2 | default(\"Agenda\") }}"
