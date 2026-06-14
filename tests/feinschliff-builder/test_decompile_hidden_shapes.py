"""Shapes flagged `hidden="1"` on their cNvPr must not reach the DSL.

PowerPoint and LibreOffice never render hidden shapes, but template
machinery loves them: corporate masters carry add-in plates (classification /
date stamps with dark theme fills and mail-merge text) flagged hidden="1" —
walked naively such a plate lands as a phantom dark rect on every decompiled
layout of the deck.
"""
from __future__ import annotations

from lxml import etree

from feinschliff_builder.decompile.pptx_svg_decompile import CanvasMap, _walk

_EMU_W, _EMU_H = 12192000, 6858000

_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _sp_xml(name: str, hidden: bool) -> str:
    hid = ' hidden="1"' if hidden else ""
    return f"""
      <p:sp xmlns:p="{_P}" xmlns:a="{_A}">
        <p:nvSpPr><p:cNvPr id="7" name="{name}"{hid}/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
        <p:spPr>
          <a:xfrm><a:off x="7670800" y="5238875"/><a:ext cx="4064000" cy="520700"/></a:xfrm>
          <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
          <a:solidFill><a:srgbClr val="111111"/></a:solidFill>
        </p:spPr>
      </p:sp>
    """


def _walk_names(*sps: str) -> list[str]:
    tree = etree.fromstring(
        f'<p:spTree xmlns:p="{_P}" xmlns:a="{_A}">{"".join(sps)}</p:spTree>'.encode()
    )
    shapes: list = []
    cmap = CanvasMap(_EMU_W, _EMU_H, 1920, 1080)
    _walk(tree, (0, 0), shapes, None, cmap, {}, {})
    return shapes


def test_hidden_sp_is_skipped():
    shapes = _walk_names(_sp_xml("Visible", hidden=False),
                         _sp_xml("HiddenDatePlate", hidden=True))
    rects = [s for s in shapes if s.kind in ("rect", "shape", "oval")]
    assert len(rects) == 1, f"hidden shape leaked into DSL shapes: {rects}"


def test_visible_sp_still_emitted():
    shapes = _walk_names(_sp_xml("Visible", hidden=False))
    assert len([s for s in shapes if s.kind in ("rect", "shape", "oval")]) == 1
