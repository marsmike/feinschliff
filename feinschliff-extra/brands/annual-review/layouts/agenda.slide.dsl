# layout: agenda — pale-blue section panel, heavy black title, numbered list. Source slide 2.
canvas 1920x1080
theme annual-review

# Signature pale-blue full-bleed SECTION panel — covers the slide except a white footer band.
rect 0,0 1757x916 fill:panel-blue

# Heavy black display title + thick black rule beneath it.
text 162,157 style:title-l weight:bold color:ink size:56pt padding:14,7,14,7 maxwidth:1230 maxheight:120 "Agenda"
line 163,295 1757,295 stroke:black stroke-width:12

# Numbered list — bold numerals, regular item titles (one bold + one regular run per row).
text 162,360 style:sub weight:bold color:ink size:28pt padding:14,7,14,7 maxwidth:120 maxheight:457 "01.\n02.\n03.\n04.\n05."
text 270,360 style:sub color:ink size:28pt padding:14,7,14,7 maxwidth:1100 maxheight:457 "Introduction\nResults from last year\nTeam\nWhat's next\nClosing"

# Footer meta on the white band: company (bold) + date + page number.
text 1307,991 style:body-sm weight:bold color:ink size:12pt padding:14,7,14,7 maxwidth:230 maxheight:29 "Annual Review"
text 1548,991 style:body-sm color:ink size:12pt padding:1 maxwidth:240 maxheight:29 "September 3, 20XX"
text 1810,991 style:body-sm color:ink size:12pt padding:14,7,14,7 maxwidth:80 maxheight:29 "2"
