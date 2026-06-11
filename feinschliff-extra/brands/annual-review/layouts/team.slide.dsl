# auto-derived from PPTX+SVG hybrid — review before use
# layout: team
canvas 1920x1080
theme annual-review

picture 162,364 288x288 path:"{{ image1 | default(\"decompile/team/image1.jpeg\") }}" cover:true
picture 596,364 288x288 path:"{{ image2 | default(\"decompile/team/image2.jpeg\") }}" cover:true
picture 1030,364 288x288 path:"{{ image3 | default(\"decompile/team/image3.jpeg\") }}" cover:true
picture 1464,364 288x288 path:"{{ image4 | default(\"decompile/team/image4.jpeg\") }}" cover:true
line 163,295 1758,296 stroke:fog stroke-width:12

text 162,157 style:sub color:black weight:bold size:44pt valign:bottom padding:1 maxwidth:1748 maxheight:102 "{{ text_1 | default(\"Our team\") }}"
text 162,679 style:body color:black weight:bold size:18pt padding:1 maxwidth:424 maxheight:63 "{{ text_2 | default(\"Ana\") }}"
text 596,682 style:body color:black weight:bold size:18pt padding:1 maxwidth:423 maxheight:63 "{{ text_3 | default(\"Larissa\") }}"
text 1029,679 style:body color:black weight:bold size:18pt padding:1 maxwidth:425 maxheight:66 "{{ text_4 | default(\"Roman\") }}"
text 1464,682 style:body color:black weight:bold size:18pt padding:1 maxwidth:446 maxheight:66 "{{ text_5 | default(\"Federico\") }}"
text 162,748 style:body color:black size:16pt padding:1 maxwidth:424 maxheight:322 "{{ text_6 | default(\"CEO\") }}"
text 596,748 style:body color:black size:16pt padding:1 maxwidth:423 maxheight:322 "{{ text_7 | default(\"CFO\") }}"
text 1029,748 style:body color:black size:16pt padding:1 maxwidth:425 maxheight:233 "{{ text_8 | default(\"CTO\") }}"
text 1464,748 style:body color:black size:16pt padding:1 maxwidth:446 maxheight:233 "{{ text_9 | default(\"COO\") }}"
text 1307,991 style:body-sm color:black size:12pt valign:middle padding:14,7,14,7 maxwidth:231 maxheight:29 "{{ text_10 | default(\"Annual Review\") }}"
text 1548,991 style:body-sm color:black size:12pt padding:1 maxwidth:252 maxheight:79 "{{ text_11 | default(\"September 3, 20XX\") }}"
text 1810,991 style:body-sm color:black size:12pt valign:middle padding:14,7,14,7 maxwidth:100 maxheight:29 "{{ text_12 | default(\"8\") }}"
