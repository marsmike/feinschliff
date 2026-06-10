# layout: summary — pale-blue full-bleed SECTION panel, heavy black title,
# two-column subhead+body grid. Footer sits ON the blue. Source slide 12.
canvas 1920x1080
theme annual-review

# Signature pale-blue full-bleed section panel — edge to edge.
rect 0,0 1920x1080 fill:panel-blue

# Heavy black display title + thick black rule beneath it.
text 147,131 style:title-l weight:bold color:ink size:56pt maxwidth:1550 maxheight:140 "Summary"
line 163,294 1757,294 stroke:black stroke-width:12

# Left column — bold subhead + regular body line each.
text 161,357 style:body weight:bold color:ink size:18pt maxwidth:768 maxheight:44 "Our business is good"
text 161,420 style:body color:ink size:18pt maxwidth:768 maxheight:44 "Profits are up in the last quarter by 3%"
text 161,547 style:body weight:bold color:ink size:18pt maxwidth:768 maxheight:44 "We’re delivering for our customers"
text 161,610 style:body color:ink size:18pt maxwidth:700 maxheight:88 "Last year we supported thousands of customers and sold 60,000 units"
text 161,780 style:body weight:bold color:ink size:18pt maxwidth:768 maxheight:44 "We’re getting our work done"
text 161,843 style:body color:ink size:18pt maxwidth:768 maxheight:44 "We finished the consolidation project"

# Right column — bold subhead + regular body line each.
text 983,347 style:body weight:bold color:ink size:18pt maxwidth:768 maxheight:44 "Our customers keep coming back"
text 983,406 style:body color:ink size:18pt maxwidth:768 maxheight:44 "We increased customer retention by 4%"
text 983,523 style:body weight:bold color:ink size:18pt maxwidth:768 maxheight:44 "We’re leaders"
text 983,582 style:body color:ink size:18pt maxwidth:720 maxheight:88 "We are top leaders in the industry across the board"

# Footer — three runs on the blue.
text 1307,983 style:body-sm size:12pt padding:14,7,14,7 maxwidth:230 maxheight:29 "Annual Review"
text 1548,983 style:body-sm size:12pt padding:1 maxwidth:240 maxheight:29 "September 3, 20XX"
text 1819,983 style:body-sm size:12pt padding:14,7,14,7 maxwidth:80 maxheight:29 "12"
