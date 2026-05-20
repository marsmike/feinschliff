# stundenplan-cell — one schedule grid cell. The fill rect is suppressed
# when `fill` is empty, so plain cells render as just text on the slide bg.
# Text color is supplied by the caller (typically "ink" for plain, "white"
# for accent/dark, "silver" for muted "—" cells).

compound stundenplan-cell(x, y, w, h, text, fill, text_color):
  rect {{ x }},{{ y }} {{ w }}x{{ h }} fill:{{ fill }}                            if:"{{ fill }}"
  text {{ x+16 }},{{ y+20 }} style:body color:{{ text_color }} maxwidth:{{ w-32 }} maxheight:40 "{{ text }}"
