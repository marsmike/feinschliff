---
role: title-primary
ideal_count: [1, 2]
data_band: none
comparison: false
variety_exempt: true
family: framing
slide_index: 1
slots:
  text_1: {role: title, chars: 78, default: Annual Review}
  text_2: {role: body, chars: 1480, default: 'Contoso Customer Success Team September 3, 20XX'}
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: cover
canvas 1920x1080
theme annual-review

rect 0,0 1920x1080 fill:paper
rect 0,0 1757x917 fill:chart-series-4
line 163,655 1757,656 stroke:fog stroke-width:20

text 154,261 style:title-l color:black size:60pt valign:bottom padding:14,7,14,7 maxwidth:1756 maxheight:333 "{{ text_1 | default(\"Annual Review\") }}"
text 163,745 style:body color:black weight:bold size:16pt padding:1 maxwidth:1747 maxheight:325 "{{ text_2 | default(\"Contoso Customer Success Team September 3, 20XX\") }}"
