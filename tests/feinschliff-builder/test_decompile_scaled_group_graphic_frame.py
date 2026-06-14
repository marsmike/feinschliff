"""A `<p:graphicFrame>` inside a SCALED group must not crash the walker.

Scaled groups (ext != chExt) thread an 8-tuple affine offset through `_walk`;
`_shape_bbox` and `_emit_cxn` unpack both tuple shapes, but
`_emit_graphic_frame` did `ox_local, oy_local = offset` and blew up with a
ValueError whenever a scaled group whose native carry declined (here: it
buries a content placeholder, so `_try_carry_group` refuses to freeze it)
contained a table/chart frame.
"""
from __future__ import annotations

from lxml import etree

from feinschliff_builder.decompile.pptx_svg_decompile import CanvasMap, _walk

_EMU_W, _EMU_H = 12192000, 6858000

_P = "http://schemas.openxmlformats.org/presentationml/2006/main"
_A = "http://schemas.openxmlformats.org/drawingml/2006/main"

# Group at (914400, 914400), child space 6096000x3048000 mapped into
# 3048000x1524000 → sx = sy = 0.5 (a SCALED group → 8-tuple offset).
# The frame is a table placeholder (`p:ph`), so `_try_carry_group` declines
# and the walker recurses into the group's children.
_TREE = f"""
<p:spTree xmlns:p="{_P}" xmlns:a="{_A}">
  <p:grpSp>
    <p:nvGrpSpPr><p:cNvPr id="2" name="ScaledGroup"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
    <p:grpSpPr>
      <a:xfrm>
        <a:off x="914400" y="914400"/><a:ext cx="3048000" cy="1524000"/>
        <a:chOff x="0" y="0"/><a:chExt cx="6096000" cy="3048000"/>
      </a:xfrm>
    </p:grpSpPr>
    <p:graphicFrame>
      <p:nvGraphicFramePr>
        <p:cNvPr id="3" name="Table 1"/><p:cNvGraphicFramePr/>
        <p:nvPr><p:ph type="tbl" idx="1"/></p:nvPr>
      </p:nvGraphicFramePr>
      <p:xfrm><a:off x="0" y="0"/><a:ext cx="6096000" cy="3048000"/></p:xfrm>
      <a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">
        <a:tbl>
          <a:tblPr/>
          <a:tblGrid><a:gridCol w="3048000"/></a:tblGrid>
          <a:tr h="370840"><a:tc>
            <a:txBody><a:bodyPr/><a:p><a:r><a:t>Cell</a:t></a:r></a:p></a:txBody>
            <a:tcPr><a:solidFill><a:srgbClr val="112233"/></a:solidFill></a:tcPr>
          </a:tc></a:tr>
        </a:tbl>
      </a:graphicData></a:graphic>
    </p:graphicFrame>
  </p:grpSp>
</p:spTree>
"""


def test_graphic_frame_in_scaled_group_does_not_crash():
    tree = etree.fromstring(_TREE.encode())
    shapes: list = []
    cmap = CanvasMap(_EMU_W, _EMU_H, 1920, 1080)
    _walk(tree, (0, 0), shapes, None, cmap, {}, {})  # pre-fix: ValueError
    assert shapes, "scaled-group table frame must still emit shapes"
    # The frame origin must land at the group's affine-mapped position:
    # ax + (0 - chox) * sx = 914400 EMU → canvas x 144.
    rects = [s for s in shapes if s.kind == "rect"]
    assert rects and rects[0].x == cmap.x(914400) and rects[0].y == cmap.y(914400)
