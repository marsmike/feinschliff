# termin-row — one event row on the termine list. Highlight rows render
# a paper-2 background fill + wiese day color + small HIGHLIGHT pill. The
# pill rect + label are suppressed for non-highlight rows via `if:`.
#
# Layout: day number (huge tief or wiese) + "JUN · MO" caption beneath,
# title centred-row, place/time mono caps right-aligned.

compound termin-row(y, day, when, title, place, day_color, row_fill, highlight):
  rect 120,{{ y }}  1680x108 fill:{{ row_fill }}                                            if:"{{ row_fill }}"
  rect 120,{{ y }}  1680x1   fill:fog
  text 128,{{ y+14 }}  style:title-l color:{{ day_color }} maxwidth:140 maxheight:80         "{{ day }}"
  text 128,{{ y+82 }}  style:detail  color:graphite        maxwidth:140 maxheight:20         "{{ when }}"
  rect 280,{{ y+38 }}  120x32 fill:accent                                                    if:"{{ highlight }}"
  text 292,{{ y+44 }}  style:detail color:white            maxwidth:108 maxheight:22         if:"{{ highlight }}" "HIGHLIGHT"
  text 420,{{ y+38 }}  style:h-hd color:black              maxwidth:1000 maxheight:40        "{{ title }}"
  text 1440,{{ y+42 }} style:detail color:steel            maxwidth:360 maxheight:28 align:right "{{ place }}"
