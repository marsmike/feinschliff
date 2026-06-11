# auto-derived from PPTX+SVG hybrid — review before use
# layout: market-overview
canvas 1920x1080
theme scientific

rect 0,0 1920x1080 fill:theme-accent2
picture 240,233 1440x613 path:"{{ image | default(\"decompile/market-overview/image.png\") }}" cover:true

text 312,302 style:title-l color:black weight:regular size:54pt valign:middle padding:14,7,14,7 maxwidth:1598 maxheight:475 "{{ text_1 | default(\"MARKET OVERVIEW\") }}"
