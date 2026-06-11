---
role: content-columns
ideal_count: [1, 1]
data_band: none
comparison: false
family: organizational
description: 'Two-column intro: left has title, rule, body paragraph; right has rectangular content photo'
slide_index: 3
slots:
  text_1: {role: title, chars: 30, default: Introduction}
  text_2: {role: body, chars: 1406, default: 'Profits are up, and losses are down! We are very proud of the progress our te…'}
  text_3: {role: footer, chars: 26, default: Annual Review}
  text_4: {role: footer, chars: 84, default: 'September 3, 20XX'}
  text_5: {role: page-number, chars: 11, default: '3'}
  image: {role: image, class: replace}
image_queries: {image: introduction}
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: introduction
canvas 1920x1080
theme annual-review

picture 1158,156 762x762 path:"{{ image | default(\"decompile/introduction/image.jpg\") }}" cover:true
line 163,294 930,295 stroke:fog stroke-width:12

text 162,157 style:sub color:black weight:bold size:44pt valign:bottom padding:1 maxwidth:986 maxheight:102 "{{ text_1 | default(\"Introduction\") }}"
text 162,360 style:body color:black size:18pt padding:1 maxwidth:986 maxheight:710 "{{ text_2 | default(\"Profits are up, and losses are down! We are very proud of the progress our team has made. Today we’ll review our wins and losses from last year and give you an overview of what you can expect for next year.\") }}"
text 1307,991 style:body-sm color:black size:12pt valign:middle padding:14,7,14,7 maxwidth:231 maxheight:29 "{{ text_3 | default(\"Annual Review\") }}"
text 1548,991 style:body-sm color:black size:12pt padding:1 maxwidth:252 maxheight:79 "{{ text_4 | default(\"September 3, 20XX\") }}"
text 1810,991 style:body-sm color:black size:12pt valign:middle padding:14,7,14,7 maxwidth:100 maxheight:29 "{{ text_5 | default(\"3\") }}"
