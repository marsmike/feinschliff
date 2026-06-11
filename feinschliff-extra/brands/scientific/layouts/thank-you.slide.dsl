---
role: closer
ideal_count: [1, 2]
data_band: none
comparison: false
variety_exempt: true
family: closing
slide_index: 13
slots:
  text_1: {role: title, chars: 132, default: THANK YOU}
  text_2: {role: body, chars: 188, default: AIDYN ZHANBOLAT | AIDYN@ADATUM.COM | WWW.ADATUM.COM}
image_queries: {image: thank you}
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: thank-you
canvas 1920x1080
theme scientific

rect 0,0 1920x1080 fill:paper
picture 780,86 360x360 path:"{{ image | default(\"decompile/thank-you/image.jpeg\") }}" cover:true

text 132,498 style:title-l color:black weight:regular size:54pt valign:middle padding:1 maxwidth:1778 maxheight:366 "{{ text_1 | default(\"THANK YOU\") }}"
text 248,952 style:body color:black size:24pt valign:top padding:1 maxwidth:1662 maxheight:118 "{{ text_2 | default(\"AIDYN ZHANBOLAT | AIDYN@ADATUM.COM | WWW.ADATUM.COM\") }}"
