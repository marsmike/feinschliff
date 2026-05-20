# stundenplan — class schedule grid: label-col 160w + 5 day columns ×
# 304 wide. Cells render via `stundenplan-cell` compound; the fill rect
# is suppressed for plain cells, painted wiese for `accent`, tief for
# `black` (dark days), or omitted with muted text for empty slots.
#
# Slot schema:
#   pgmeta    string  — header eyebrow
#   title     string  — slide title
#   days      array, 5 strings — column headers
#   rows      array, 5 objects:
#       hour    string — e.g. "1. STD"
#       time    string — e.g. "08:00"
#       cells   array, 5 objects: { text, fill, text_color }
#                                    fill ∈ "" | "accent" | "black"
#                                    text_color ∈ "ink" | "white" | "silver"
#   legend    string — abbreviation line at bottom
# Deck-level: footer_left, footer_center, footer_right.

canvas 1920x1080
theme gs-ramspau

header pgmeta:"{{ pgmeta }}"

text 120,230 style:title-l color:black maxwidth:1680 maxheight:90 "{{ title }}"

# === Grid frame ===
# Geometry: x=120 (label col 160w) ; days at x=280, 584, 888, 1192, 1496 (304 stride).
# Top hairline, header row (60h), 5 rows × 76h.
rect 120,360  1680x1 fill:fog

# Day headers (mono caps).
text 296,378  style:detail color:graphite maxwidth:288 maxheight:28 "{{ days[0] }}"
text 600,378  style:detail color:graphite maxwidth:288 maxheight:28 "{{ days[1] }}"
text 904,378  style:detail color:graphite maxwidth:288 maxheight:28 "{{ days[2] }}"
text 1208,378 style:detail color:graphite maxwidth:288 maxheight:28 "{{ days[3] }}"
text 1512,378 style:detail color:graphite maxwidth:288 maxheight:28 "{{ days[4] }}"
rect 120,420  1680x1 fill:fog

# === Row 1 — y=420..496 ===
text 136,438  style:detail color:graphite maxwidth:144 maxheight:24 "{{ rows[0].hour }}"
text 136,464  style:detail color:steel    maxwidth:144 maxheight:20 "{{ rows[0].time }}"
stundenplan-cell x:280  y:420 w:304 h:76 text:"{{ rows[0].cells[0].text }}" fill:"{{ rows[0].cells[0].fill }}" text_color:"{{ rows[0].cells[0].text_color }}"
stundenplan-cell x:584  y:420 w:304 h:76 text:"{{ rows[0].cells[1].text }}" fill:"{{ rows[0].cells[1].fill }}" text_color:"{{ rows[0].cells[1].text_color }}"
stundenplan-cell x:888  y:420 w:304 h:76 text:"{{ rows[0].cells[2].text }}" fill:"{{ rows[0].cells[2].fill }}" text_color:"{{ rows[0].cells[2].text_color }}"
stundenplan-cell x:1192 y:420 w:304 h:76 text:"{{ rows[0].cells[3].text }}" fill:"{{ rows[0].cells[3].fill }}" text_color:"{{ rows[0].cells[3].text_color }}"
stundenplan-cell x:1496 y:420 w:304 h:76 text:"{{ rows[0].cells[4].text }}" fill:"{{ rows[0].cells[4].fill }}" text_color:"{{ rows[0].cells[4].text_color }}"
rect 120,496  1680x1 fill:fog

# === Row 2 — y=496..572 ===
text 136,514  style:detail color:graphite maxwidth:144 maxheight:24 "{{ rows[1].hour }}"
text 136,540  style:detail color:steel    maxwidth:144 maxheight:20 "{{ rows[1].time }}"
stundenplan-cell x:280  y:496 w:304 h:76 text:"{{ rows[1].cells[0].text }}" fill:"{{ rows[1].cells[0].fill }}" text_color:"{{ rows[1].cells[0].text_color }}"
stundenplan-cell x:584  y:496 w:304 h:76 text:"{{ rows[1].cells[1].text }}" fill:"{{ rows[1].cells[1].fill }}" text_color:"{{ rows[1].cells[1].text_color }}"
stundenplan-cell x:888  y:496 w:304 h:76 text:"{{ rows[1].cells[2].text }}" fill:"{{ rows[1].cells[2].fill }}" text_color:"{{ rows[1].cells[2].text_color }}"
stundenplan-cell x:1192 y:496 w:304 h:76 text:"{{ rows[1].cells[3].text }}" fill:"{{ rows[1].cells[3].fill }}" text_color:"{{ rows[1].cells[3].text_color }}"
stundenplan-cell x:1496 y:496 w:304 h:76 text:"{{ rows[1].cells[4].text }}" fill:"{{ rows[1].cells[4].fill }}" text_color:"{{ rows[1].cells[4].text_color }}"
rect 120,572  1680x1 fill:fog

# === Row 3 — y=572..648 ===
text 136,590  style:detail color:graphite maxwidth:144 maxheight:24 "{{ rows[2].hour }}"
text 136,616  style:detail color:steel    maxwidth:144 maxheight:20 "{{ rows[2].time }}"
stundenplan-cell x:280  y:572 w:304 h:76 text:"{{ rows[2].cells[0].text }}" fill:"{{ rows[2].cells[0].fill }}" text_color:"{{ rows[2].cells[0].text_color }}"
stundenplan-cell x:584  y:572 w:304 h:76 text:"{{ rows[2].cells[1].text }}" fill:"{{ rows[2].cells[1].fill }}" text_color:"{{ rows[2].cells[1].text_color }}"
stundenplan-cell x:888  y:572 w:304 h:76 text:"{{ rows[2].cells[2].text }}" fill:"{{ rows[2].cells[2].fill }}" text_color:"{{ rows[2].cells[2].text_color }}"
stundenplan-cell x:1192 y:572 w:304 h:76 text:"{{ rows[2].cells[3].text }}" fill:"{{ rows[2].cells[3].fill }}" text_color:"{{ rows[2].cells[3].text_color }}"
stundenplan-cell x:1496 y:572 w:304 h:76 text:"{{ rows[2].cells[4].text }}" fill:"{{ rows[2].cells[4].fill }}" text_color:"{{ rows[2].cells[4].text_color }}"
rect 120,648  1680x1 fill:fog

# === Row 4 — y=648..724 ===
text 136,666  style:detail color:graphite maxwidth:144 maxheight:24 "{{ rows[3].hour }}"
text 136,692  style:detail color:steel    maxwidth:144 maxheight:20 "{{ rows[3].time }}"
stundenplan-cell x:280  y:648 w:304 h:76 text:"{{ rows[3].cells[0].text }}" fill:"{{ rows[3].cells[0].fill }}" text_color:"{{ rows[3].cells[0].text_color }}"
stundenplan-cell x:584  y:648 w:304 h:76 text:"{{ rows[3].cells[1].text }}" fill:"{{ rows[3].cells[1].fill }}" text_color:"{{ rows[3].cells[1].text_color }}"
stundenplan-cell x:888  y:648 w:304 h:76 text:"{{ rows[3].cells[2].text }}" fill:"{{ rows[3].cells[2].fill }}" text_color:"{{ rows[3].cells[2].text_color }}"
stundenplan-cell x:1192 y:648 w:304 h:76 text:"{{ rows[3].cells[3].text }}" fill:"{{ rows[3].cells[3].fill }}" text_color:"{{ rows[3].cells[3].text_color }}"
stundenplan-cell x:1496 y:648 w:304 h:76 text:"{{ rows[3].cells[4].text }}" fill:"{{ rows[3].cells[4].fill }}" text_color:"{{ rows[3].cells[4].text_color }}"
rect 120,724  1680x1 fill:fog

# === Row 5 — y=724..800 ===
text 136,742  style:detail color:graphite maxwidth:144 maxheight:24 "{{ rows[4].hour }}"
text 136,768  style:detail color:steel    maxwidth:144 maxheight:20 "{{ rows[4].time }}"
stundenplan-cell x:280  y:724 w:304 h:76 text:"{{ rows[4].cells[0].text }}" fill:"{{ rows[4].cells[0].fill }}" text_color:"{{ rows[4].cells[0].text_color }}"
stundenplan-cell x:584  y:724 w:304 h:76 text:"{{ rows[4].cells[1].text }}" fill:"{{ rows[4].cells[1].fill }}" text_color:"{{ rows[4].cells[1].text_color }}"
stundenplan-cell x:888  y:724 w:304 h:76 text:"{{ rows[4].cells[2].text }}" fill:"{{ rows[4].cells[2].fill }}" text_color:"{{ rows[4].cells[2].text_color }}"
stundenplan-cell x:1192 y:724 w:304 h:76 text:"{{ rows[4].cells[3].text }}" fill:"{{ rows[4].cells[3].fill }}" text_color:"{{ rows[4].cells[3].text_color }}"
stundenplan-cell x:1496 y:724 w:304 h:76 text:"{{ rows[4].cells[4].text }}" fill:"{{ rows[4].cells[4].fill }}" text_color:"{{ rows[4].cells[4].text_color }}"

# Legend below the grid.
text 120,830 style:detail color:steel maxwidth:1680 maxheight:40 "{{ legend }}"

footer left:"{{ footer_left }}" center:"{{ footer_center }}" right:"{{ footer_right }}"
