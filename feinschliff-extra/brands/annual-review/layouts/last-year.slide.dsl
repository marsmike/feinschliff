---
role: title-with-visual
ideal_count: [1, 1]
data_band: none
comparison: false
family: image-driven
slide_index: 4
slots:
  text_1: {role: title, chars: 54, default: Last year}
image_queries: {image: last year}
---
# auto-derived from PPTX+SVG hybrid — review before use
# layout: last-year
canvas 1920x1080
theme annual-review

picture 0,0 1920x1080 path:"{{ image | default(\"decompile/last-year/image.png\") }}" cover:true
line 164,293 1755,294 stroke:fog stroke-width:12
line 163,296 1757,297 stroke:fog stroke-width:12

text 162,157 style:sub color:black weight:bold size:44pt valign:bottom padding:1 maxwidth:1748 maxheight:102 "{{ text_1 | default(\"Last year\") }}"
