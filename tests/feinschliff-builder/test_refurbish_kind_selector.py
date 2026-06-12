from __future__ import annotations

from feinschliff_builder.diagrams.refurbish.ir import ExtractedDiagram, Node
from feinschliff_builder.diagrams.refurbish.kind_selector import select_kind


def _ir(signals: dict, n_nodes: int = 3) -> ExtractedDiagram:
    return ExtractedDiagram(
        nodes=[Node(id=str(i), label=f"n{i}", type="rect", x=0, y=0, w=10, h=10) for i in range(n_nodes)],
        signals=signals,
    )


def test_boxes_and_arrows_selects_excalidraw():
    assert select_kind(_ir({"boxes_and_arrows": True})) == "excalidraw"


def test_bars_selects_svg():
    assert select_kind(_ir({"bars": True})) == "svg"


def test_axis_selects_svg():
    assert select_kind(_ir({"axis": True})) == "svg"


def test_ambiguous_defaults_excalidraw():
    assert select_kind(_ir({})) == "excalidraw"
