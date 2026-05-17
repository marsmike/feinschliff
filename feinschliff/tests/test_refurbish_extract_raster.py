from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from lib.diagrams.refurbish.extract_raster import extract_from_image
from lib.diagrams.refurbish.ir import ExtractedDiagram


_MOCK_LLM_RESPONSE = {
    "nodes": [
        {"id": "a", "label": "Source", "type": "rect", "x": 100, "y": 100, "w": 200, "h": 80},
        {"id": "b", "label": "Sink",   "type": "rect", "x": 400, "y": 100, "w": 200, "h": 80},
    ],
    "edges": [{"from_id": "a", "to_id": "b", "kind": "arrow"}],
    "signals": {"boxes_and_arrows": True, "bars": False, "axis": False, "freeform": False},
}


def test_raster_extract_with_mocked_llm(tmp_path):
    img = tmp_path / "diagram.png"
    img.write_bytes(b"\x89PNG\r\n" + b"\x00" * 100)

    with patch(
        "lib.diagrams.refurbish.extract_raster._call_claude_vision",
        return_value=_MOCK_LLM_RESPONSE,
    ):
        ir = extract_from_image(img)

    assert isinstance(ir, ExtractedDiagram)
    assert len(ir.nodes) == 2
    assert len(ir.edges) == 1
    assert ir.confidence < 1.0  # raster never fully confident (defaults to 0.5)
