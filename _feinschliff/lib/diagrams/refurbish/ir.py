"""Intermediate representation for refurbish — extracted from old PPTX,
emitted to excalidraw or SVG DSL by the kind selector + emitter."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field


@dataclass
class Node:
    id: str
    label: str
    type: str  # "rect" | "ellipse" | "freeform" | "bar"
    x: int
    y: int
    w: int
    h: int


@dataclass
class Edge:
    from_id: str
    to_id: str
    kind: str = "arrow"


@dataclass
class ExtractedDiagram:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    signals: dict = field(default_factory=dict)
    confidence: float = 1.0

    def to_json(self) -> str:
        return json.dumps({
            "nodes": [asdict(n) for n in self.nodes],
            "edges": [asdict(e) for e in self.edges],
            "signals": self.signals,
            "confidence": self.confidence,
        }, indent=2)

    @classmethod
    def from_json(cls, s: str) -> ExtractedDiagram:
        d = json.loads(s)
        return cls(
            nodes=[Node(**n) for n in d.get("nodes", [])],
            edges=[Edge(**e) for e in d.get("edges", [])],
            signals=d.get("signals", {}),
            confidence=d.get("confidence", 1.0),
        )
