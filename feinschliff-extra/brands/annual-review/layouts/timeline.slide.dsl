# layout: timeline — full-bleed warm-yellow panel, heavy black title, four quarter columns. Source slide 9.
canvas 1920x1080
theme annual-review

# Full-bleed warm-yellow section panel — footer sits on the yellow, no white band.
rect 0,0 1920x1080 fill:panel-yellow

# Heavy black display title + thick black rule beneath it.
text 150,157 style:title-l weight:bold color:ink size:56pt maxwidth:1550 maxheight:140 "Timeline"
line 163,295 1757,295 stroke:black stroke-width:12

# Four quarter columns: bold label, date range, lorem body. Sizes/x/y measured
# off source slide-9 so the rendered glyph edges land on the source's (the
# Noto fallback LibreOffice substitutes for Arial Nova renders ~1.27x larger,
# so column type is sized down and the body wraps at 306px to reproduce the
# source's six-line break pattern instead of over-wrapping to eight lines).
text 147,349 style:body weight:bold color:ink size:17pt maxwidth:330 maxheight:44 "Q1."
text 149,407 style:body color:ink size:18pt maxwidth:330 maxheight:44 "Jul - Sep"
text 149,513 style:body color:ink size:12pt maxwidth:306 maxheight:210 "Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna."

text 561,349 style:body weight:bold color:ink size:17pt maxwidth:330 maxheight:44 "Q1."
text 561,408 style:body color:ink size:18pt maxwidth:330 maxheight:44 "Oct - Dec"
text 557,513 style:body color:ink size:12pt maxwidth:306 maxheight:210 "Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna."

text 976,349 style:body weight:bold color:ink size:17pt maxwidth:330 maxheight:44 "Q3."
text 978,408 style:body color:ink size:18pt maxwidth:330 maxheight:44 "Jan - Mar"
text 974,514 style:body color:ink size:12pt maxwidth:306 maxheight:210 "Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna."

text 1390,349 style:body weight:bold color:ink size:17pt maxwidth:330 maxheight:44 "Q4."
text 1388,408 style:body color:ink size:18pt maxwidth:330 maxheight:44 "Apr - Jun"
text 1389,513 style:body color:ink size:12pt maxwidth:306 maxheight:210 "Lorem ipsum dolor sit amet, consectetuer adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna."

# Footer runs on the yellow.
text 1307,991 style:body-sm weight:bold color:ink size:12pt maxwidth:230 maxheight:29 "Annual Review"
text 1548,991 style:body-sm color:ink size:12pt maxwidth:240 maxheight:29 "September 3, 20XX"
text 1810,991 style:body-sm color:ink size:12pt maxwidth:80 maxheight:29 "9"
