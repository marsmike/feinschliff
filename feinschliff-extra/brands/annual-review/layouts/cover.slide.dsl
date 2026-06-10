# layout: cover — warm-yellow section panel, heavy black title, org line. Source slide 1.
canvas 1920x1080
theme annual-review

# Signature warm-yellow panel — inset, leaving a white margin at right + bottom.
rect 0,0 1758x916 fill:panel-yellow

# Heavy black display title + thick black rule beneath it.
text 150,440 style:title-l weight:bold color:ink size:64pt maxwidth:1550 maxheight:180 "Annual Review"
line 163,655 1758,656 stroke:black stroke-width:14

# Org line: company (bold) + team + date, as three runs across.
text 160,745 style:body weight:bold color:ink size:18pt maxwidth:200 maxheight:44 "Contoso"
text 340,745 style:body color:ink size:18pt maxwidth:430 maxheight:44 "Customer Success Team"
text 750,745 style:body color:ink size:18pt maxwidth:320 maxheight:44 "September 3, 20XX"
