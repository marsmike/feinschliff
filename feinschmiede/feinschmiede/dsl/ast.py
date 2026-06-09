"""Typed AST for the feinschliff slide DSL.

Provides first-class domain types for the parsed/expanded representation
of a slide deck:

- :class:`ElementKind` — enum of element types
- :class:`Element` — a single DSL element (text, rect, picture, diagram, …)
- :class:`Slide` — one slide, carrying its layout name + element list
- :class:`Document` — the full deck AST

The ``to_dict`` / ``from_dict`` round-trip is designed to be compatible
with the shape produced by ``feinschliff.dsl.parser.parse()`` after normalisation.
New code should use :func:`feinschliff.dsl.parser.parse_document` to get a
``Document`` directly.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ElementKind(str, Enum):
    """Discriminant for DSL element nodes.

    String values match the DSL primitive/block names where possible so
    serialisation is transparent.
    """
    TEXT = "text"
    IMAGE = "image"           # picture primitive
    SHAPE = "shape"           # rect / shape primitives
    DIAGRAM = "diagram"       # svg / excalidraw blocks
    GROUP = "group"           # logical grouping (for-loops, sections)
    COMPOUND = "compound"     # unresolved compound call


# ---------------------------------------------------------------------------
# Element
# ---------------------------------------------------------------------------

@dataclass
class Element:
    """One DSL element in a slide.

    Parameters
    ----------
    kind:
        The element discriminant.
    props:
        Key-value properties (keyword arguments, label, geometry, etc.).
        Structure is kind-specific but always dict-serialisable.
    children:
        Nested elements (e.g. inside a GROUP or COMPOUND body).
    """
    kind: ElementKind
    props: dict[str, Any] = field(default_factory=dict)
    children: list[Element] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"kind": self.kind.value}
        if self.props:
            d["props"] = copy.deepcopy(self.props)
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Element":
        kind = ElementKind(d["kind"])
        props = copy.deepcopy(d.get("props") or {})
        children = [cls.from_dict(c) for c in (d.get("children") or [])]
        return cls(kind=kind, props=props, children=children)


# ---------------------------------------------------------------------------
# Slide
# ---------------------------------------------------------------------------

@dataclass
class Slide:
    """One slide in the deck.

    Parameters
    ----------
    layout:
        The layout DSL file stem, e.g. ``'title-orange'``.
    elements:
        The element list for this slide.
    meta:
        Slide-level metadata (theme, canvas size, notes, etc.).
    notes:
        Speaker-notes text, if any.
    """
    layout: str = ""
    elements: list[Element] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"layout": self.layout}
        if self.elements:
            d["elements"] = [e.to_dict() for e in self.elements]
        if self.meta:
            d["meta"] = copy.deepcopy(self.meta)
        if self.notes is not None:
            d["notes"] = self.notes
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Slide":
        layout = d.get("layout") or ""
        elements = [Element.from_dict(e) for e in (d.get("elements") or [])]
        meta = copy.deepcopy(d.get("meta") or {})
        notes = d.get("notes")
        return cls(layout=layout, elements=elements, meta=meta, notes=notes)


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

@dataclass
class Document:
    """The full deck AST.

    Parameters
    ----------
    version:
        Schema version integer (currently ``1``).
    slides:
        Ordered list of slides.
    meta:
        Deck-level metadata (title, brand, etc.).
    """
    version: int = 1
    slides: list[Slide] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "slides": [s.to_dict() for s in self.slides],
            "meta": copy.deepcopy(self.meta),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Document":
        version = int(d.get("version") or 1)
        slides = [Slide.from_dict(s) for s in (d.get("slides") or [])]
        meta = copy.deepcopy(d.get("meta") or {})
        return cls(version=version, slides=slides, meta=meta)
