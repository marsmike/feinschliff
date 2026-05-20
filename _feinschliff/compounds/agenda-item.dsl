# Standard agenda-item compound. Emits a top hairline + mono counter +
# title + description. Entire item is skipped (no hairline emitted) when
# the `title` slot is empty — keeps tail positions clean.

compound agenda-item(x, y, w, counter, title, description):
  rect {{ x }},{{ y }} {{ w }}x1 fill:fog                                                       if:"{{ title }}"
  text {{ x }},{{ y+18 }}     style:agenda-num maxwidth:100              maxheight:24           if:"{{ title }}" "{{ counter }}"
  text {{ x+110 }},{{ y+8 }}  style:agenda-t   maxwidth:{{ w-110 }}      maxheight:38           if:"{{ title }}" "{{ title }}"
  text {{ x+110 }},{{ y+52 }} style:agenda-d   maxwidth:{{ w-110 }}      maxheight:36           if:"{{ title }}" "{{ description }}"
