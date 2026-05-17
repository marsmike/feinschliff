# `card-q` compound — quarterly variant. Same shape as `card` but with a
# smaller col-title (28px instead of 36px) for narrower 4-column grids.
# Matches the canonical four-column slide where col-t is inline-overridden.

compound card-q(x, y, w, h, counter, heading, body):
  rect {{ x }},{{ y }} {{ w }}x{{ h }} fill:paper
  text {{ x+40 }},{{ y+40 }}  style:col-num     maxwidth:{{ w-80 }} maxheight:24              "{{ counter }}"
  text {{ x+40 }},{{ y+84 }}  style:col-title-q maxwidth:{{ w-80 }} maxheight:140             "{{ heading }}"
  text {{ x+40 }},{{ y+236 }} style:col-body    maxwidth:{{ w-80 }} maxheight:80              "{{ body }}"
