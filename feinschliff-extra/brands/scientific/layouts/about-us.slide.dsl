---
role: content-columns
ideal_count: [1, 1]
data_band: none
comparison: false
family: organizational
description: 'About us: full-width lab close-up photo banner top, large centred title, blue dash rule, body tagline below'
slide_index: 3
slots:
  text_1: {role: title, chars: 132, default: ABOUT US}
  text_2: {role: body, chars: 202, default: Aiming to revolutionize industries through our forward-thinking solutions}
  image: {role: image, class: replace}
image_queries: {image: about us}
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: about-us
canvas 1920x1080
theme scientific

picture 0,0 1920x373 path:"{{ image | default(\"decompile/about-us/image.png\") }}" cover:true

text 132,425 style:title-l color:black weight:regular size:54pt autoshrink:true valign:middle padding:14,7,14,7 maxwidth:1778 maxheight:410 "{{ text_1 | default(\"ABOUT US\") }}"
text 132,952 style:body color:black size:24pt autoshrink:true padding:1 maxwidth:1778 maxheight:118 "{{ text_2 | default(\"Aiming to revolutionize industries through our forward-thinking solutions\") }}"
