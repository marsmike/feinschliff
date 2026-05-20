"""Raster diagram extraction via Claude vision.

Call site `_call_claude_vision` is separated so tests can mock it.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

from .ir import ExtractedDiagram, Node, Edge


_PROMPT = """\
You are an expert at reading hand-drawn or auto-generated diagrams.

Look at this image. Identify:
- Boxes / shapes (with labels)
- Lines / arrows between them
- Whether this is a flow/architecture (boxes_and_arrows) or a chart (bars/axis)

Output a JSON object with this exact shape:
{
  "nodes": [{"id": "a", "label": "...", "type": "rect|ellipse", "x": 0, "y": 0, "w": 0, "h": 0}, ...],
  "edges": [{"from_id": "a", "to_id": "b", "kind": "arrow"}, ...],
  "signals": {"boxes_and_arrows": true|false, "bars": ..., "axis": ..., "freeform": ...}
}

Coordinates in image pixels. Be conservative — only mark what you can clearly see.
Output ONLY the JSON, no prose.
"""


def extract_from_image(path: Path, confidence_floor: float = 0.5) -> ExtractedDiagram:
    response = _call_claude_vision(path)
    if isinstance(response, str):
        response = json.loads(response)
    return ExtractedDiagram(
        nodes=[Node(**n) for n in response.get("nodes", [])],
        edges=[Edge(**e) for e in response.get("edges", [])],
        signals=response.get("signals", {}),
        confidence=response.get("confidence", confidence_floor),
    )


def _call_claude_vision(path: Path) -> dict:
    """Wrap the actual Anthropic API call. Mockable in tests."""
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise RuntimeError(
            "extract_from_image: anthropic library not installed; "
            "refurbish raster path requires `uv pip install anthropic`"
        ) from exc

    client = Anthropic()
    img_b64 = base64.standard_b64encode(path.read_bytes()).decode()
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": "image/png", "data": img_b64,
                }},
                {"type": "text", "text": _PROMPT},
            ],
        }],
    )
    return json.loads(response.content[0].text)
