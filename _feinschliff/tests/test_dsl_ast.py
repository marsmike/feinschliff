"""Tests for lib.dsl.ast — Document/Slide/Element AST dataclasses."""
from __future__ import annotations

import pytest

from lib.dsl.ast import Document, Element, ElementKind, Slide


# ---------------------------------------------------------------------------
# ElementKind
# ---------------------------------------------------------------------------

def test_element_kind_is_str_enum():
    assert ElementKind.TEXT == "text"
    assert isinstance(ElementKind.TEXT, str)


def test_element_kind_values():
    assert ElementKind.TEXT.value == "text"
    assert ElementKind.IMAGE.value == "image"
    assert ElementKind.SHAPE.value == "shape"
    assert ElementKind.DIAGRAM.value == "diagram"
    assert ElementKind.GROUP.value == "group"
    assert ElementKind.COMPOUND.value == "compound"


def test_element_kind_from_string():
    assert ElementKind("text") is ElementKind.TEXT
    assert ElementKind("diagram") is ElementKind.DIAGRAM


def test_element_kind_invalid_raises():
    with pytest.raises(ValueError):
        ElementKind("unknown-kind")


# ---------------------------------------------------------------------------
# Element
# ---------------------------------------------------------------------------

def test_element_defaults():
    e = Element(kind=ElementKind.TEXT)
    assert e.kind is ElementKind.TEXT
    assert e.props == {}
    assert e.children == []


def test_element_to_dict_minimal():
    e = Element(kind=ElementKind.TEXT)
    d = e.to_dict()
    assert d["kind"] == "text"
    assert "props" not in d
    assert "children" not in d


def test_element_to_dict_with_props_and_children():
    child = Element(kind=ElementKind.TEXT, props={"label": "child"})
    e = Element(
        kind=ElementKind.GROUP,
        props={"x": 0, "y": 0},
        children=[child],
    )
    d = e.to_dict()
    assert d["kind"] == "group"
    assert d["props"] == {"x": 0, "y": 0}
    assert len(d["children"]) == 1
    assert d["children"][0]["kind"] == "text"


def test_element_from_dict_roundtrip():
    original = Element(
        kind=ElementKind.SHAPE,
        props={"fill": "accent", "x": 100, "y": 200},
        children=[Element(kind=ElementKind.TEXT, props={"label": "hi"})],
    )
    restored = Element.from_dict(original.to_dict())
    assert restored.kind is original.kind
    assert restored.props == original.props
    assert len(restored.children) == 1
    assert restored.children[0].kind is ElementKind.TEXT


def test_element_from_dict_no_props_or_children():
    d = {"kind": "image"}
    e = Element.from_dict(d)
    assert e.kind is ElementKind.IMAGE
    assert e.props == {}
    assert e.children == []


def test_element_props_are_deep_copied():
    props = {"color": [1, 2, 3]}
    e = Element(kind=ElementKind.TEXT, props=props)
    d = e.to_dict()
    d["props"]["color"].append(4)
    assert e.props["color"] == [1, 2, 3]  # original unchanged


# ---------------------------------------------------------------------------
# Slide
# ---------------------------------------------------------------------------

def test_slide_defaults():
    s = Slide()
    assert s.layout == ""
    assert s.elements == []
    assert s.meta == {}
    assert s.notes is None


def test_slide_to_dict_minimal():
    s = Slide(layout="title-orange")
    d = s.to_dict()
    assert d["layout"] == "title-orange"
    assert "elements" not in d
    assert "meta" not in d
    assert "notes" not in d


def test_slide_to_dict_with_notes():
    s = Slide(layout="body", notes="Speaker note here")
    d = s.to_dict()
    assert d["notes"] == "Speaker note here"


def test_slide_from_dict_roundtrip():
    s = Slide(
        layout="my-layout",
        elements=[Element(kind=ElementKind.TEXT, props={"label": "hello"})],
        meta={"theme": "dark"},
        notes="Some note",
    )
    d = s.to_dict()
    r = Slide.from_dict(d)
    assert r.layout == "my-layout"
    assert len(r.elements) == 1
    assert r.elements[0].kind is ElementKind.TEXT
    assert r.meta == {"theme": "dark"}
    assert r.notes == "Some note"


def test_slide_from_dict_missing_fields():
    d = {}
    s = Slide.from_dict(d)
    assert s.layout == ""
    assert s.elements == []
    assert s.meta == {}
    assert s.notes is None


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

def test_document_defaults():
    doc = Document()
    assert doc.version == 1
    assert doc.slides == []
    assert doc.meta == {}


def test_document_to_dict_empty():
    doc = Document()
    d = doc.to_dict()
    assert d["version"] == 1
    assert d["slides"] == []
    assert d["meta"] == {}


def test_document_from_dict_roundtrip():
    doc = Document(
        version=1,
        slides=[
            Slide(
                layout="title-orange",
                elements=[Element(kind=ElementKind.TEXT, props={"label": "Title"})],
                notes="Hook",
            ),
            Slide(layout="body-2col", meta={"canvas": "1920x1080"}),
        ],
        meta={"brand": "feinschliff", "title": "My Deck"},
    )
    d = doc.to_dict()
    r = Document.from_dict(d)

    assert r.version == 1
    assert len(r.slides) == 2
    assert r.slides[0].layout == "title-orange"
    assert r.slides[0].notes == "Hook"
    assert r.slides[0].elements[0].props == {"label": "Title"}
    assert r.slides[1].layout == "body-2col"
    assert r.slides[1].meta == {"canvas": "1920x1080"}
    assert r.meta == {"brand": "feinschliff", "title": "My Deck"}


def test_document_version_defaults_to_1():
    d = {"slides": []}
    doc = Document.from_dict(d)
    assert doc.version == 1


def test_document_roundtrip_equality():
    """Dict → Document → dict must be equal (no data loss)."""
    raw = {
        "version": 1,
        "slides": [
            {
                "layout": "title-split",
                "elements": [
                    {"kind": "text", "props": {"label": "Hello", "style": "title"}},
                    {"kind": "shape", "props": {"fill": "accent"}},
                ],
                "notes": "speak here",
            }
        ],
        "meta": {"deck": "demo"},
    }
    doc = Document.from_dict(raw)
    result = doc.to_dict()
    assert result == raw


def test_element_kind_serialises_to_string_value():
    """Ensure ElementKind.TEXT serialises to 'text', not 'ElementKind.TEXT'."""
    e = Element(kind=ElementKind.TEXT, props={"x": 1})
    d = e.to_dict()
    assert d["kind"] == "text"
    assert isinstance(d["kind"], str)
