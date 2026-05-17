# Standard `card` compound — one column in a multi-column-cards slide.
#
# Matches canonical .col.card: paper background, 40px padding, gap 20px
# between counter / heading / body. col-n (14px mono gold) above col-t
# (36px medium) above col-b (22px graphite).

compound card(x, y, w, h, counter, heading, body):
  rect {{ x }},{{ y }} {{ w }}x{{ h }} fill:paper
  text {{ x+40 }},{{ y+40 }}  style:col-num   maxwidth:{{ w-80 }} maxheight:24                "{{ counter }}"
  text {{ x+40 }},{{ y+84 }}  style:col-title maxwidth:{{ w-80 }} maxheight:140               "{{ heading }}"
  text {{ x+40 }},{{ y+236 }} style:col-body  maxwidth:{{ w-80 }} maxheight:80                "{{ body }}"
