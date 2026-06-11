# auto-derived from PPTX+SVG hybrid — review before use
# layout: thank-you
canvas 1920x1080
theme annual-review

picture 0,156 762x762 path:"{{ image | default(\"decompile/thank-you/image.jpeg\") }}" cover:true
line 986,294 1753,295 stroke:fog stroke-width:12

text 985,157 style:sub color:black weight:bold size:44pt valign:bottom padding:1 maxwidth:925 maxheight:102 "{{ text_1 | default(\"Thank you\") }}"
text 985,360 style:body color:black size:18pt padding:1 maxwidth:925 maxheight:367 "{{ text_2 | default(\"Thanks to your commitment and strong work ethic, we know next year will be even better than the last.\nWe look forward to working together.\") }}"
text 985,734 style:body color:black weight:bold size:16pt valign:top padding:1 maxwidth:925 maxheight:247 "{{ text_3 | default(\"Contoso\nsales@contoso.com\") }}"
text 1307,991 style:body-sm color:black size:12pt valign:middle padding:14,7,14,7 maxwidth:231 maxheight:29 "{{ text_4 | default(\"Annual Review\") }}"
text 1548,991 style:body-sm color:black size:12pt padding:1 maxwidth:252 maxheight:79 "{{ text_5 | default(\"September 3, 20XX\") }}"
text 1810,991 style:body-sm color:black size:12pt valign:middle padding:14,7,14,7 maxwidth:100 maxheight:29 "{{ text_6 | default(\"13\") }}"
