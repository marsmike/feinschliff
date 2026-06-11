---
role: content-columns
ideal_count: [1, 1]
data_band: none
comparison: false
family: organizational
slide_index: 6
slots:
  text_1: {role: title, chars: 160, default: MARKET OVERVIEW}
image_queries: {image: market overview}
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: market-overview
canvas 1920x1080
theme scientific

rect 0,0 1920x1080 fill:theme-accent2
picture 240,233 1440x613 path:"{{ image | default(\"decompile/market-overview/image.png\") }}" cover:true

text 312,302 style:title-l color:black weight:regular size:54pt valign:middle padding:14,7,14,7 maxwidth:1598 maxheight:475 "{{ text_1 | default(\"MARKET OVERVIEW\") }}"
