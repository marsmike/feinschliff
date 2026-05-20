from __future__ import annotations

from pathlib import Path

from feinschliff.diagrams.diagram_wireframe import primitives_from_svg_dsl, primitives_from_excalidraw_dsl


def _brand_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "brands" / "feinschliff"


def test_svg_dsl_yields_bbox_primitives():
    dsl = """
canvas 600x400
rect bg 0,0 600x400 paper
bar b1 100,100 80x200 primary value:"$85k"
text t1 300,30 title "Q1 Revenue"
"""
    prims = primitives_from_svg_dsl(dsl, _brand_dir())
    kinds = [p.kind for p in prims]
    assert "rect" in kinds
    assert "text" in kinds
    assert kinds.count("rect") >= 2  # bg + bar


def test_excalidraw_dsl_yields_bbox_primitives():
    dsl = """
canvas 800x600
box api 100,100 200x80 "API"
box svc 400,100 200x80 "Service"
arrow api -> svc
"""
    prims = primitives_from_excalidraw_dsl(dsl, _brand_dir())
    kinds = [p.kind for p in prims]
    assert kinds.count("rect") == 2
    assert "text" in kinds
    assert "line" in kinds
