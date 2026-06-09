from __future__ import annotations

from pathlib import Path

from feinschliff_builder.diagrams.refurbish.ir import ExtractedDiagram, Node, Edge
from feinschliff_builder.diagrams.refurbish.emit_excalidraw import emit
from feinschmiede.diagrams.excalidraw_expand import expand


def test_emit_excalidraw_roundtrips_through_expand():
    ir = ExtractedDiagram(
        nodes=[
            Node(id="a", label="Source", type="rect", x=100, y=100, w=200, h=80),
            Node(id="b", label="Sink",   type="rect", x=400, y=100, w=200, h=80),
        ],
        edges=[Edge(from_id="a", to_id="b", kind="arrow")],
    )
    dsl = emit(ir, canvas_w=800, canvas_h=400)
    assert "canvas 800x400" in dsl
    assert 'box a' in dsl
    assert 'box b' in dsl
    assert "arrow a -> b" in dsl
    brand_dir = Path(__file__).resolve().parents[2] / "feinschliff" / "brands" / "feinschliff"
    j = expand(dsl, brand_dir=brand_dir)
    assert "rectangle" in j
    assert "arrow" in j
