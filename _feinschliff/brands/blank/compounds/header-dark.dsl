# Feinschliff header — dark-mode variant. Light wordmark + faded pgmeta
# on the ink/accent ground. Use on layouts with fill:ink (and on
# fill:accent if the eyebrow/text colors are inverted to white).

compound header-dark(pgmeta):
  # Light gem (navy ramp on dark background, legible). Marked optional
  # for the same reason as `header` — descendant brands that don't ship
  # a gem still render cleanly with just the wordmark text.
  picture 100,52 22x26 path:gem-light.png optional:true
  text 132,56 style:wordmark color:white maxwidth:300 "FEINSCHLIFF."
  text 1100,56 style:pgmeta color:off-white-2 maxwidth:720 "{{ pgmeta }}" align:right
