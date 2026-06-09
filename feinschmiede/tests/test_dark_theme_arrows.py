"""Dark-theme arrows must contrast with the canvas (regression: invisible arrows).

In `theme dark` the default arrow ink (`ink`) resolved to the same dark color as
the chapter-slab background, so arrows disappeared. The default must flip to a
light token in dark theme while explicit `color:` stays honored.
"""

import json

from feinschmiede.brand_discovery import find_brand
from feinschmiede.diagrams.excalidraw_expand import expand

_BRAND = find_brand("feinschliff").root

_DARK = (
    "canvas 800x300\n"
    "theme dark\n"
    'box a 40,90 200x100 "A" fill:start\n'
    'box b 460,90 200x100 "B" fill:primary\n'
    'arrow a -> b label:"x"\n'
)


def _doc(dsl: str) -> dict:
    return json.loads(expand(dsl, _BRAND))


def test_dark_default_arrow_stroke_not_equal_background():
    doc = _doc(_DARK)
    bg = doc["appState"]["viewBackgroundColor"].lower()
    arrows = [e for e in doc["elements"] if e["type"] == "arrow"]
    assert arrows, "no arrow emitted"
    for ar in arrows:
        assert ar["strokeColor"].lower() != bg, "dark-theme arrow stroke equals background (invisible)"


def test_dark_arrow_label_not_equal_background():
    doc = _doc(_DARK)
    bg = doc["appState"]["viewBackgroundColor"].lower()
    labels = [e for e in doc["elements"] if e["type"] == "text" and e.get("text") == "x"]
    assert labels, "no arrow label emitted"
    assert labels[0]["strokeColor"].lower() != bg


def test_light_theme_arrow_default_unchanged():
    light = _DARK.replace("theme dark\n", "")
    doc = _doc(light)
    arrows = [e for e in doc["elements"] if e["type"] == "arrow"]
    # Light-theme default stays `ink` (dark on light paper) — behavior preserved.
    from feinschmiede.diagrams.brand_bridge import resolve

    assert arrows[0]["strokeColor"].lower() == resolve("ink", _BRAND).lower()


def test_explicit_color_honored_in_dark():
    dsl = _DARK.replace('arrow a -> b label:"x"', 'arrow a -> b color:accent label:"x"')
    doc = _doc(dsl)
    from feinschmiede.diagrams.brand_bridge import resolve

    arrows = [e for e in doc["elements"] if e["type"] == "arrow"]
    assert arrows[0]["strokeColor"].lower() == resolve("accent", _BRAND).lower()
