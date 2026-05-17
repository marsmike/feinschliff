# termine — chronological events list. 5 rows, each rendered via the
# `termin-row` compound which handles highlight-row treatment (paper-2
# row fill, wiese day color, HIGHLIGHT pill).
#
# Slot schema:
#   pgmeta    string — eyebrow
#   title     string — slide title
#   events    array, 5 objects:
#       day        string ≤2 (e.g. "22")
#       when       string ≤10 (e.g. "JUN · MO")
#       title      string
#       place      string ≤40 (mono caps, right-aligned)
#       highlight  bool — "true" to fill the row + show pill
#       day_color  string — "black" (default tief) or "accent" (highlight rows)
#       row_fill   string — "" or "paper-2"
# Deck-level: footer_left, footer_center, footer_right.

canvas 1920x1080
theme gs-ramspau

header pgmeta:"{{ pgmeta }}"

text 120,230 style:title-l color:black maxwidth:1680 maxheight:90 "{{ title }}"

# 5 rows × 108 tall, y=380..920.
termin-row y:380 day:"{{ events[0].day }}" when:"{{ events[0].when }}" title:"{{ events[0].title }}" place:"{{ events[0].place }}" day_color:"{{ events[0].day_color }}" row_fill:"{{ events[0].row_fill }}" highlight:"{{ events[0].highlight }}"
termin-row y:488 day:"{{ events[1].day }}" when:"{{ events[1].when }}" title:"{{ events[1].title }}" place:"{{ events[1].place }}" day_color:"{{ events[1].day_color }}" row_fill:"{{ events[1].row_fill }}" highlight:"{{ events[1].highlight }}"
termin-row y:596 day:"{{ events[2].day }}" when:"{{ events[2].when }}" title:"{{ events[2].title }}" place:"{{ events[2].place }}" day_color:"{{ events[2].day_color }}" row_fill:"{{ events[2].row_fill }}" highlight:"{{ events[2].highlight }}"
termin-row y:704 day:"{{ events[3].day }}" when:"{{ events[3].when }}" title:"{{ events[3].title }}" place:"{{ events[3].place }}" day_color:"{{ events[3].day_color }}" row_fill:"{{ events[3].row_fill }}" highlight:"{{ events[3].highlight }}"
termin-row y:812 day:"{{ events[4].day }}" when:"{{ events[4].when }}" title:"{{ events[4].title }}" place:"{{ events[4].place }}" day_color:"{{ events[4].day_color }}" row_fill:"{{ events[4].row_fill }}" highlight:"{{ events[4].highlight }}"

# Bottom hairline.
rect 120,920 1680x1 fill:fog

footer left:"{{ footer_left }}" center:"{{ footer_center }}" right:"{{ footer_right }}"
