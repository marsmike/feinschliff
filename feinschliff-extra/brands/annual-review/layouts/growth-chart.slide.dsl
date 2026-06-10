# layout: growth-chart — pale-blue section panel, heavy black title, horizontal
# grouped bar chart (4 categories x 3 series). Source slide 5.
canvas 1920x1080
theme annual-review

# Signature pale-blue full-bleed panel — covers all but a white footer band.
rect 0,0 1757x916 fill:panel-blue

# Heavy black display title + thick black rule beneath it.
text 162,180 style:title-l weight:bold color:ink size:56pt maxwidth:1550 maxheight:140 "Growth by sector chart"
line 163,295 1757,295 stroke:black stroke-width:12

# ── Grouped horizontal bar chart ──────────────────────────────────────
# Axis origin x=337 (tick "0"); ticks 0..6 at x 337,539,742,945,1147,1350,1553
# → ~202.67 px per unit. Within each category, three contiguous 20px-tall
# bars, top→bottom: Series 3 (black), Series 2 (teal), Series 1 (white/paper).
# Bar widths measured from source slide-05 (len in px = value × ppu).

# Category 4 (top): S3=5.0(1013) S2=2.8(567) S1=4.5(911)
rect 337,388 1013x20 fill:chart-series-3
rect 337,407 567x20 fill:chart-series-2
rect 337,427 911x20 fill:paper

# Category 3: S3=3.0(607) S2=1.8(364) S1=3.5(709)
rect 337,483 607x20 fill:chart-series-3
rect 337,502 364x20 fill:chart-series-2
rect 337,522 709x20 fill:paper

# Category 2: S3=2.0(405) S2=4.4(891) S1=2.5(506)
rect 337,577 405x20 fill:chart-series-3
rect 337,597 891x20 fill:chart-series-2
rect 337,617 506x20 fill:paper

# Category 1 (bottom): S3=2.0(405) S2=2.4(486) S1=4.3(871)
rect 337,672 405x20 fill:chart-series-3
rect 337,692 486x20 fill:chart-series-2
rect 337,711 871x20 fill:paper

# Category labels (left of plot, bold black, centered on each group).
text 161,401 style:body weight:bold color:ink size:18pt maxwidth:185 maxheight:32 valign:middle "Category 4"
text 161,495 style:body weight:bold color:ink size:18pt maxwidth:185 maxheight:32 valign:middle "Category 3"
text 161,591 style:body weight:bold color:ink size:18pt maxwidth:185 maxheight:32 valign:middle "Category 2"
text 161,684 style:body weight:bold color:ink size:18pt maxwidth:185 maxheight:32 valign:middle "Category 1"

# X-axis tick labels (0–6) below the plot; box x = digit-left − inset, so the
# glyph centers land on each gridline (337,539,742,945,1147,1350,1553).
text 312,755 style:body-sm color:ink size:18pt maxwidth:40 maxheight:30 "0"
text 516,755 style:body-sm color:ink size:18pt maxwidth:40 maxheight:30 "1"
text 718,755 style:body-sm color:ink size:18pt maxwidth:40 maxheight:30 "2"
text 920,755 style:body-sm color:ink size:18pt maxwidth:40 maxheight:30 "3"
text 1122,755 style:body-sm color:ink size:18pt maxwidth:40 maxheight:30 "4"
text 1326,755 style:body-sm color:ink size:18pt maxwidth:40 maxheight:30 "5"
text 1529,755 style:body-sm color:ink size:18pt maxwidth:40 maxheight:30 "6"

# Legend (below plot): swatch + label, S3 / S2 / S1, swatches ~13px at y=829.
rect 694,829 13x13 fill:chart-series-3
text 704,825 style:body-sm color:ink size:16pt maxwidth:120 maxheight:26 "Series 3"
rect 816,829 14x13 fill:chart-series-2
text 826,825 style:body-sm color:ink size:16pt maxwidth:120 maxheight:26 "Series 2"
rect 939,829 13x13 fill:paper
text 949,825 style:body-sm color:ink size:16pt maxwidth:120 maxheight:26 "Series 1"

# Footer meta (three runs), on the white band.
text 1307,991 style:body-sm weight:bold color:ink size:12pt maxwidth:230 maxheight:29 "Annual Review"
text 1548,991 style:body-sm color:ink size:12pt maxwidth:240 maxheight:29 "September 3, 20XX"
text 1810,991 style:body-sm color:ink size:12pt maxwidth:80 maxheight:29 "5"
