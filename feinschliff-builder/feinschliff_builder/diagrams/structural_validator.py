"""Compatibility shim — the diagram structural validator moved into the engine.

The implementation now lives in ``feinschmiede.diagrams.structural_validator``
(shared so feinbild + the deck can both use it) and emits engine-native defects.
This shim re-exposes the same function names but adapts results to the office
``feinschliff.defects.Defect`` taxonomy, so feinschliff-builder's
``verify-diagram`` CLI + reports keep working unchanged.
"""
from __future__ import annotations

from feinschliff.defects import Defect, from_engine_defect
from feinschmiede.diagrams import structural_validator as _engine


def _adapt(defects) -> list[Defect]:
    return [from_engine_defect(d) for d in defects]


def validate_excalidraw_structure(doc) -> list[Defect]:
    return _adapt(_engine.validate_excalidraw_structure(doc))


def validate_svg_structure(svg_text) -> list[Defect]:
    return _adapt(_engine.validate_svg_structure(svg_text))


def validate_excalidraw_file(path) -> list[Defect]:
    return _adapt(_engine.validate_excalidraw_file(path))


def validate_svg_file(path) -> list[Defect]:
    return _adapt(_engine.validate_svg_file(path))


def validate_diagram_file(path) -> list[Defect]:
    return _adapt(_engine.validate_diagram_file(path))
