# Feinschliff header — gem icon + FEINSCHLIFF. wordmark top-left,
# pgmeta line top-right. Matches the canonical layout chrome exactly.

compound header(pgmeta):
  # Gem icon (navy diamond polygon, rendered once as PNG asset). Marked
  # optional so descendant brands that don't ship a gem (e.g. `claude`
  # extends `feinschliff` but uses its own wordmark only) don't trip the
  # missing-asset fatal policy.
  picture 100,55 22x26 path:gem.png optional:true
  # Wordmark — `style:wordmark` carries medium weight + letter-spacing + uppercase
  # transform. Canonical SVG sets font-size:18 font-weight:500 letter-spacing:3.
  text 132,56 style:wordmark maxwidth:300 "FEINSCHLIFF."
  # Top-right meta line — `style:pgmeta` applies the canonical .pgmeta opacity 0.7 + uppercase
  text 1100,56 style:pgmeta maxwidth:720 "{{ pgmeta }}" align:right
