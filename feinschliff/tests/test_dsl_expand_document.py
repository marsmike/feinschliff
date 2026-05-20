"""Tests for expand_document — typed Document expansion entry point."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from lib.brand import BrandPack
from lib.dsl.ast import Document, Element, ElementKind, Slide
from lib.dsl.expander import expand_document
from lib.dsl.parser import parse_document


def _make_pack(tmp_path: Path, name: str = "test-brand") -> BrandPack:
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "tokens.json").write_text(json.dumps({
        "color": {"accent": {"$value": "#C9A24A"}, "paper": "#FAF8F3"},
    }))
    return BrandPack.load(d)


def test_expand_document_returns_document(tmp_path):
    doc = parse_document("text 100,100 \"Hello\"\n")
    pack = _make_pack(tmp_path)
    result = expand_document(doc, pack)
    assert isinstance(result, Document)


def test_expand_document_preserves_version(tmp_path):
    doc = Document(version=1, slides=[Slide(layout="x")])
    pack = _make_pack(tmp_path)
    result = expand_document(doc, pack)
    assert result.version == 1


def test_expand_document_preserves_slide_count(tmp_path):
    doc = Document(slides=[Slide(layout="a"), Slide(layout="b")])
    pack = _make_pack(tmp_path)
    result = expand_document(doc, pack)
    assert len(result.slides) == 2


def test_expand_document_preserves_primitive_elements(tmp_path):
    """Text elements (primitives) pass through expand unchanged."""
    doc = parse_document('text 100,100 "Hello"\nrect 0,0 1920x100 fill:accent\n')
    pack = _make_pack(tmp_path)
    result = expand_document(doc, pack)
    assert len(result.slides[0].elements) == 2
    assert result.slides[0].elements[0].kind is ElementKind.TEXT
    assert result.slides[0].elements[1].kind is ElementKind.SHAPE


def test_expand_document_does_not_mutate_input(tmp_path):
    """expand_document must not mutate the input Document."""
    doc = parse_document('text 0,0 "X"\n')
    pack = _make_pack(tmp_path)
    original_slide_layout = doc.slides[0].layout
    original_element_count = len(doc.slides[0].elements)
    expand_document(doc, pack)
    assert doc.slides[0].layout == original_slide_layout
    assert len(doc.slides[0].elements) == original_element_count


def test_expand_document_with_brand_compound(tmp_path):
    """A compound defined in the brand's compounds/ gets expanded."""
    pack = _make_pack(tmp_path)
    compounds = tmp_path / "test-brand" / "compounds"
    compounds.mkdir()
    (compounds / "myfooter.dsl").write_text(
        'compound myfooter():\n  rect 0,1040 1920x4 fill:accent\n'
    )
    # Reload pack so it picks up compounds/
    pack = BrandPack.load(tmp_path / "test-brand")

    dsl = "myfooter\n"
    doc = parse_document(dsl)
    result = expand_document(doc, pack)
    # The compound should be expanded to a SHAPE (rect)
    assert any(el.kind is ElementKind.SHAPE for el in result.slides[0].elements)


def test_expand_document_preserves_slide_notes(tmp_path):
    """Slide notes survive expand_document unchanged."""
    doc = Document(slides=[Slide(layout="x", notes="My note")])
    pack = _make_pack(tmp_path)
    result = expand_document(doc, pack)
    assert result.slides[0].notes == "My note"
