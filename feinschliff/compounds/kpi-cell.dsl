# Standard `kpi-cell` compound — one cell of a kpi-grid.
#
# Canonical .kpi: padding 36 40, hairlines top/right/bottom (the grid
# contributes the left), min-height 260. Internal hierarchy:
#   v (120px light, ink) with optional inline unit (40px graphite)
#   k (16px mono uppercase graphite, 32px above)
#   delta (18px mono accent-hover, 10px above)
#
# Caller supplies the top-left (x, y), cell width and height.

compound kpi-cell(x, y, w, h, value, unit, label, delta):
  rect {{ x }},{{ y }}        {{ w }}x1   fill:fog
  rect {{ x }},{{ y+h-1 }}    {{ w }}x1   fill:fog
  rect {{ x+w-1 }},{{ y }}    1x{{ h }}   fill:fog
  # Value bbox widened 170 → 250 so 3-digit tnum values fit at the
  # 120px kpi-value font (e.g. "441" ≈ 210px wide). Unit shifted right
  # by 60px to make room; still fits 2-char units like "%" or "M".
  text {{ x+40 }},{{ y+36 }}   style:kpi-value maxwidth:250          maxheight:140 "{{ value }}"
  text {{ x+300 }},{{ y+86 }}  style:kpi-unit  maxwidth:90           maxheight:60  "{{ unit }}"
  text {{ x+40 }},{{ y+184 }}  style:kpi-key   maxwidth:{{ w-80 }}                 "{{ label }}"
  text {{ x+40 }},{{ y+216 }}  style:kpi-delta maxwidth:{{ w-80 }}                 "{{ delta }}"
