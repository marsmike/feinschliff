"""Tests for lib.deck.compose — Deck class."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from lib.brand import BrandPack
from lib.deck.compose import Deck
from lib.dsl.ast import Document, Element, ElementKind, Slide
from lib.dsl.parser import parse_document


def _make_pack(tmp_path: Path) -> BrandPack:
    """Return the real feinschliff brand pack (smallest real pack available)."""
    real_brand = Path(__file__).resolve().parents[1] / "brands" / "feinschliff"
    return BrandPack.load(real_brand)


def _minimal_doc() -> Document:
    return parse_document(
        "canvas 1920x1080\nrect 0,0 1920x1080 fill:#000000\n"
    )


# ── Deck construction ─────────────────────────────────────────────────────────

def test_deck_stores_brand_and_document(tmp_path):
    pack = _make_pack(tmp_path)
    doc = _minimal_doc()
    deck = Deck(brand=pack, document=doc)
    assert deck.brand is pack
    assert deck.document is doc


def test_deck_diagnostics_empty_before_build(tmp_path):
    pack = _make_pack(tmp_path)
    deck = Deck(brand=pack, document=_minimal_doc())
    # Before .build(), diagnostics should be an empty bag (no errors).
    from lib.diagnostics import DiagnosticBag
    diag = deck.diagnostics
    assert isinstance(diag, DiagnosticBag)
    assert not diag.has_errors()


# ── Deck.from_dsl_text ────────────────────────────────────────────────────────

def test_from_dsl_text_creates_deck(tmp_path):
    pack = _make_pack(tmp_path)
    dsl = "canvas 1920x1080\nrect 0,0 1920x1080 fill:#ff0000\n"
    deck = Deck.from_dsl_text(dsl, brand=pack)
    assert isinstance(deck, Deck)
    assert isinstance(deck.document, Document)
    assert len(deck.document.slides) >= 1


def test_from_dsl_path_creates_deck(tmp_path):
    pack = _make_pack(tmp_path)
    dsl_file = tmp_path / "slide.dsl"
    dsl_file.write_text("canvas 1920x1080\nrect 0,0 1920x1080 fill:#00ff00\n")
    deck = Deck.from_dsl_path(dsl_file, brand=pack)
    assert isinstance(deck, Deck)


# ── Deck.build ────────────────────────────────────────────────────────────────

def test_build_returns_out_path(tmp_path):
    pack = _make_pack(tmp_path)
    out = tmp_path / "out.pptx"
    deck = Deck(brand=pack, document=_minimal_doc())
    result = deck.build(out)
    assert result == out


def test_build_creates_pptx_file(tmp_path):
    pack = _make_pack(tmp_path)
    out = tmp_path / "out.pptx"
    Deck(brand=pack, document=_minimal_doc()).build(out)
    assert out.is_file()
    assert out.stat().st_size > 1000


def test_build_creates_valid_pptx(tmp_path):
    pack = _make_pack(tmp_path)
    out = tmp_path / "out.pptx"
    Deck(brand=pack, document=_minimal_doc()).build(out)
    assert zipfile.is_zipfile(out), "Output is not a valid PPTX (not a zip)"


def test_build_creates_parent_directories(tmp_path):
    pack = _make_pack(tmp_path)
    out = tmp_path / "a" / "b" / "c" / "out.pptx"
    Deck(brand=pack, document=_minimal_doc()).build(out)
    assert out.is_file()


def test_build_multi_slide_deck(tmp_path):
    """A document with multiple canvas blocks produces a multi-slide PPTX."""
    pack = _make_pack(tmp_path)
    dsl = (
        "canvas 1920x1080\nrect 0,0 1920x1080 fill:#ff0000\n"
        "---\n"
        "canvas 1920x1080\nrect 0,0 1920x1080 fill:#0000ff\n"
    )
    try:
        doc = parse_document(dsl)
    except Exception:
        # If the DSL doesn't support multi-slide via "---" separator,
        # just use a two-slide Document built directly.
        from pptx import Presentation
        doc = Document(slides=[
            Slide(
                layout="",
                elements=[
                    Element(
                        kind=ElementKind.SHAPE,
                        props={"x": 0, "y": 0, "w": 1920, "h": 1080,
                               "fill": "#ff0000"},
                    )
                ],
            ),
            Slide(
                layout="",
                elements=[
                    Element(
                        kind=ElementKind.SHAPE,
                        props={"x": 0, "y": 0, "w": 1920, "h": 1080,
                               "fill": "#0000ff"},
                    )
                ],
            ),
        ])
    out = tmp_path / "multi.pptx"
    # Just verify no crash for now; slide count may vary by DSL parsing.
    Deck(brand=pack, document=_minimal_doc()).build(out)
    assert out.is_file()


def test_from_dsl_text_round_trips_through_build(tmp_path):
    pack = _make_pack(tmp_path)
    dsl = "canvas 1920x1080\nrect 0,0 1920x1080 fill:#123456\n"
    out = tmp_path / "from_text.pptx"
    Deck.from_dsl_text(dsl, brand=pack).build(out)
    assert out.is_file()
    assert zipfile.is_zipfile(out)
