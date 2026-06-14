from __future__ import annotations

from pathlib import Path

from feinschliff_builder.diagrams.refurbish.ir import ExtractedDiagram, Node
from feinschliff_builder.diagrams.refurbish.emit_svg import emit
from feinschmiede.diagrams.svg_expand import expand


def test_emit_svg_for_bars():
    ir = ExtractedDiagram(
        nodes=[
            Node(id="b1", label="$85k", type="bar", x=100, y=100, w=80, h=200),
            Node(id="b2", label="$62k", type="bar", x=200, y=150, w=80, h=150),
        ],
        signals={"bars": True},
    )
    dsl = emit(ir, canvas_w=600, canvas_h=400)
    assert "canvas 600x400" in dsl
    assert "bar b1" in dsl
    assert "bar b2" in dsl
    brand_dir = Path(__file__).resolve().parents[2] / "feinschliff" / "brands" / "feinschliff"
    svg = expand(dsl, brand_dir=brand_dir)
    assert "<svg" in svg
    assert svg.count("<rect") >= 2
