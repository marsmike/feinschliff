---
role: content-columns
ideal_count: [4, 4]
data_band: none
comparison: false
family: organizational
slide_index: 10
slots:
  text_1: {role: title, chars: 54, default: Goals for Q1}
  text_2: {role: body, chars: 124, default: Business priorities}
  text_3: {role: body, chars: 140, default: Employee opportunities}
  text_4: {role: body, chars: 976, default: Increase customer satisfaction by 2%\nMaintain growth\nDiversify investment i…}
  text_5: {role: body, chars: 897, default: End of fiscal celebration on July 15th\nEmployee day of learning on August 14…}
  text_6: {role: footer, chars: 26, default: Annual Review}
  text_7: {role: footer, chars: 84, default: 'September 3, 20XX'}
  text_8: {role: page-number, chars: 11, default: '10'}
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: goals-q1
canvas 1920x1080
theme annual-review

line 163,295 1758,296 stroke:fog stroke-width:12

text 162,157 style:sub color:black weight:bold size:44pt valign:bottom padding:1 maxwidth:1748 maxheight:102 "{{ text_1 | default(\"Goals for Q1\") }}"
text 148,367 style:body color:black weight:bold size:18pt padding:14,7,14,7 maxwidth:828 maxheight:102 "{{ text_2 | default(\"Business priorities\") }}"
text 986,367 style:body color:black weight:bold size:18pt padding:14,7,14,7 maxwidth:924 maxheight:102 "{{ text_3 | default(\"Employee opportunities\") }}"
text 163,479 style:body color:black size:18pt valign:top padding:1 maxwidth:817 maxheight:591 "{{ text_4 | default(\"Increase customer satisfaction by 2%\nMaintain growth\nDiversify investment in sector 2\nInitiative partnership with 3rd party organizations\") }}"
text 990,479 style:body color:black size:18pt valign:top padding:1 maxwidth:920 maxheight:502 "{{ text_5 | default(\"End of fiscal celebration on July 15th\nEmployee day of learning on August 14th\nEmployee Yoga on September 3rd\nSeminar series begins September 10th\") }}"
text 1307,991 style:body-sm color:black size:12pt valign:middle padding:14,7,14,7 maxwidth:231 maxheight:29 "{{ text_6 | default(\"Annual Review\") }}"
text 1548,991 style:body-sm color:black size:12pt padding:1 maxwidth:252 maxheight:79 "{{ text_7 | default(\"September 3, 20XX\") }}"
text 1810,991 style:body-sm color:black size:12pt valign:middle padding:14,7,14,7 maxwidth:100 maxheight:29 "{{ text_8 | default(\"10\") }}"
