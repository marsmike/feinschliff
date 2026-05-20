from __future__ import annotations

from lib.diagrams.refurbish.ir import ExtractedDiagram, Node, Edge


def test_ir_serialization_roundtrip():
    ir = ExtractedDiagram(
        nodes=[
            Node(id="a", label="A", type="rect", x=0, y=0, w=100, h=50),
            Node(id="b", label="B", type="rect", x=200, y=0, w=100, h=50),
        ],
        edges=[Edge(from_id="a", to_id="b", kind="arrow")],
        signals={"boxes_and_arrows": True},
        confidence=1.0,
    )
    j = ir.to_json()
    rt = ExtractedDiagram.from_json(j)
    assert rt.nodes[0].label == "A"
    assert rt.edges[0].from_id == "a"
    assert rt.signals == {"boxes_and_arrows": True}
    assert rt.confidence == 1.0
