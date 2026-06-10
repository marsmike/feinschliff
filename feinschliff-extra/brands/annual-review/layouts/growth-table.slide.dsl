# layout: growth-table — warm-yellow section panel, heavy black title, native data table. Source slide 6.
canvas 1920x1080
theme annual-review

# Signature warm-yellow panel — inset, leaving a white footer band at the bottom (matches cover).
rect 0,0 1757x918 fill:panel-yellow

# Heavy black display title + thick black rule beneath it.
text 147,134 style:title-l weight:bold color:ink size:52pt maxwidth:1590 maxheight:130 "Growth by sector table"
line 163,295 1757,295 stroke:black stroke-width:12

# Table grid — thin white vertical separators between value columns (y 381..732). Source draws these white, not fog.
line 447,381 447,732 stroke:white stroke-width:2
line 732,381 732,732 stroke:white stroke-width:2
line 1018,381 1018,732 stroke:white stroke-width:2
line 1303,381 1303,732 stroke:white stroke-width:2
line 1589,381 1589,732 stroke:white stroke-width:2

# Black horizontal rules under the header row and each data row.
line 162,468 1590,468 stroke:black stroke-width:2
line 162,556 1590,556 stroke:black stroke-width:2
line 162,644 1590,644 stroke:black stroke-width:2

# Header row — empty corner, then Q1..Q4 (bold, centered).
text 462,403 style:body weight:bold color:ink size:18pt align:center maxwidth:257 maxheight:60 "Q1"
text 747,403 style:body weight:bold color:ink size:18pt align:center maxwidth:257 maxheight:60 "Q2"
text 1033,403 style:body weight:bold color:ink size:18pt align:center maxwidth:257 maxheight:60 "Q3"
text 1319,403 style:body weight:bold color:ink size:18pt align:center maxwidth:257 maxheight:60 "Q4"

# Data rows — bold row-label on the left, regular centered values.
text 176,491 style:body weight:bold color:ink size:18pt align:center maxwidth:257 maxheight:60 "Series 1"
text 462,491 style:body color:ink size:18pt align:center maxwidth:257 maxheight:60 "4.3"
text 747,491 style:body color:ink size:18pt align:center maxwidth:257 maxheight:60 "2.5"
text 1033,491 style:body color:ink size:18pt align:center maxwidth:257 maxheight:60 "3.5"
text 1319,491 style:body color:ink size:18pt align:center maxwidth:257 maxheight:60 "4.5"
text 176,579 style:body weight:bold color:ink size:18pt align:center maxwidth:257 maxheight:60 "Series 2"
text 462,579 style:body color:ink size:18pt align:center maxwidth:257 maxheight:60 "2.4"
text 747,579 style:body color:ink size:18pt align:center maxwidth:257 maxheight:60 "4.4"
text 1033,579 style:body color:ink size:18pt align:center maxwidth:257 maxheight:60 "1.8"
text 1319,579 style:body color:ink size:18pt align:center maxwidth:257 maxheight:60 "2.8"
text 176,667 style:body weight:bold color:ink size:18pt align:center maxwidth:257 maxheight:60 "Series 3"
text 462,667 style:body color:ink size:18pt align:center maxwidth:257 maxheight:60 "2"
text 747,667 style:body color:ink size:18pt align:center maxwidth:257 maxheight:60 "2"
text 1033,667 style:body color:ink size:18pt align:center maxwidth:257 maxheight:60 "3"
text 1319,667 style:body color:ink size:18pt align:center maxwidth:257 maxheight:60 "5"

# Footer — three runs across the white band.
text 1307,983 style:body-sm color:ink size:12pt padding:14,7,14,7 maxwidth:230 maxheight:29 "Annual Review"
text 1548,983 style:body-sm color:ink size:12pt padding:1 maxwidth:240 maxheight:29 "September 3, 20XX"
text 1810,983 style:body-sm color:ink size:12pt padding:14,7,14,7 maxwidth:80 maxheight:29 "6"
