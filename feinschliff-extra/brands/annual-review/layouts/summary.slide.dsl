# auto-derived from PPTX+SVG hybrid — review before use
# layout: summary
canvas 1920x1080
theme annual-review

rect 0,0 1920x1080 fill:highlight
line 163,295 1758,296 stroke:fog stroke-width:12

text 162,157 style:sub color:black weight:bold size:44pt valign:bottom padding:1 maxwidth:1748 maxheight:102 "{{ text_1 | default(\"Summary\") }}"
text 984,360 style:body color:black weight:bold size:18pt padding:14,7,14,7 maxwidth:926 maxheight:621 "{{ text_2 | default(\"Our customers keep coming back\nWe increased customer retention by 4%\nWe’re leaders\nWe are top leaders in the industry across the board\") }}"
text 162,366 style:body color:black weight:bold size:18pt padding:14,7,14,7 maxwidth:812 maxheight:704 "{{ text_3 | default(\"Our business is good\nProfits are up in the last quarter by 3%\nWe’re delivering for our customers\nLast year we supported thousands of customers and sold 60,000 units\nWe’re getting our work done\nWe finished the consolidation project\") }}"
text 1307,991 style:body-sm color:black size:12pt valign:middle padding:14,7,14,7 maxwidth:231 maxheight:29 "{{ text_4 | default(\"Annual Review\") }}"
text 1548,991 style:body-sm color:black size:12pt padding:1 maxwidth:252 maxheight:79 "{{ text_5 | default(\"September 3, 20XX\") }}"
text 1810,991 style:body-sm color:black size:12pt valign:middle padding:14,7,14,7 maxwidth:100 maxheight:29 "{{ text_6 | default(\"12\") }}"
