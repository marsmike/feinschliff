"""The master's `<p:clrMap>` must drive bg1/tx1/bg2/tx2 slot resolution.

Dark-master templates (e.g. MS gallery "Annual Review") INVERT the default
mapping — `<p:clrMap bg1="dk1" tx1="lt1" …>` — so a layout background of
`schemeClr val="tx1"` is WHITE and the master title's `bg1` is BLACK.
Assuming the default mapping renders those decks colour-inverted (black
cover, white-on-yellow invisible titles).
"""
from __future__ import annotations

from pptx import Presentation

from feinschliff_builder.decompile.pptx_svg_decompile import load_theme_scheme

_P = "http://schemas.openxmlformats.org/presentationml/2006/main"


def _clrmap(prs):
    return prs.slide_masters[0].element.find(f"{{{_P}}}clrMap")


def test_default_clr_map_keeps_standard_aliases():
    prs = Presentation()
    theme = load_theme_scheme(prs)
    assert theme["bg1"] == theme["lt1"]
    assert theme["tx1"] == theme["dk1"]


def test_inverted_clr_map_swaps_bg_and_tx():
    prs = Presentation()
    cm = _clrmap(prs)
    cm.set("bg1", "dk1")
    cm.set("tx1", "lt1")
    cm.set("bg2", "dk2")
    cm.set("tx2", "lt2")
    theme = load_theme_scheme(prs)
    assert theme["bg1"] == theme["dk1"], "bg1 must follow the master clrMap"
    assert theme["tx1"] == theme["lt1"], "tx1 must follow the master clrMap"
    assert theme["bg2"] == theme["dk2"]
    assert theme["tx2"] == theme["lt2"]
