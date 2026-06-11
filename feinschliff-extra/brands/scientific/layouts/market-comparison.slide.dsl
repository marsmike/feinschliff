# auto-derived from PPTX+SVG hybrid — review before use
# layout: market-comparison
canvas 1920x1080
theme scientific

rect 1056,0 864x1080 fill:paper-2
picture 202,86 475x475 path:"{{ image | default(\"decompile/market-comparison/image.jpeg\") }}" cover:true
line 204,963 269,964 stroke:theme-accent1 stroke-width:14

text 1135,115 style:body color:black size:24pt autoshrink:true valign:bottom padding:14,7,14,7 maxwidth:775 maxheight:850 "{{ text_1 | default(\"STANDS OUT IN MARKET\nINNOVATIVE FEATURES\nPROVIDES UNIQUE SOLUTION\nEDGE OVER COMPETITORS\nUSER-FOCUSED DESIGN\nPRIORITIZES USER EXPERIENCE\") }}"
text 202,619 style:sub color:black size:32pt valign:bottom padding:1 maxwidth:844 maxheight:288 "{{ text_2 | default(\"MARKET COMPARISON\") }}"
