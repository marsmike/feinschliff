---
role: concept-diagram
ideal_count: [8, 20]
data_band: none
comparison: false
narrative_role: system
diagram_complexity: deep
description: 'Full-slide Excalidraw diagram with minimal chrome: thin eyebrow/title strip top, diagram fills remaining height'
---
# excalidraw-diagram-full — full-slide deep architecture diagram (10-20+
# nodes, zones, typed arrows). Use when the audience is technical and the
# diagram needs to preserve mechanisms, interfaces, and trade-offs that a
# narrow-band 8-node diagram would lose.
#
# Renders at virtual canvas 6880x2880 (4× the 1720x720 slot) so the model
# has 16× the pixel area to author into. PowerPoint downscales on insert
# for effectively high-DPI output.
#
# Slot schema:
#   logo, pgmeta, tracker, action_title — shared
#   diagram_dsl   string, required — excalidraw DSL body (no `canvas` line;
#                                    the layout's virtual:6880x2880 IS the canvas)
#   so_what       optional — omitted on deep diagrams by default; embed
#                             interpretive callouts inside the diagram instead

canvas 1920x1080
theme feinschliff

header pgmeta:"{{ pgmeta }}"

rect 100,180 80x4 fill:ink
text 100,220 style:eyebrow maxwidth:1720 maxheight:30 "{{ tracker }}"
text 100,260 style:title   maxwidth:1720 maxheight:60 "{{ action_title }}"

excalidraw diagram 100,340 1720x720 virtual:6880x2880 {
  {{ diagram_dsl }}
}

text 100,1060 style:detail color:graphite maxwidth:1720 maxheight:20 if:"{{ so_what }}" "So what: {{ so_what }}"

# Note: `source` slot dropped — text at y=1080 overflowed canvas edge.
# Cite via speaker notes (deck-level `notes:` per slide) instead.

footer left:"{{ footer_left }}" right:"{{ footer_right }}"
