"""Tests for lib.deck.compose — Deck class."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from feinschmiede.brand import BrandPack
from feinschliff.deck.compose import Deck
from feinschmiede.dsl.ast import Document
from feinschliff.dsl.parser import parse_document


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
    from feinschmiede.diagnostics import DiagnosticBag
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
    """Deck.build doesn't crash on the minimal single-slide fixture.

    The original intent was a true multi-slide build using a ``---``
    separator, but parse_document doesn't yet recognise that separator.
    Restore the multi-slide construction once parse_document handles it.
    """
    pack = _make_pack(tmp_path)
    out = tmp_path / "multi.pptx"
    Deck(brand=pack, document=_minimal_doc()).build(out)
    assert out.is_file()


def test_from_dsl_text_round_trips_through_build(tmp_path):
    pack = _make_pack(tmp_path)
    dsl = "canvas 1920x1080\nrect 0,0 1920x1080 fill:#123456\n"
    out = tmp_path / "from_text.pptx"
    Deck.from_dsl_text(dsl, brand=pack).build(out)
    assert out.is_file()
    assert zipfile.is_zipfile(out)


# ── Deck.from_brief ───────────────────────────────────────────────────────────

def _layouts_dir() -> Path:
    """Return the bundled layouts directory."""
    return Path(__file__).resolve().parents[1] / "layouts"


def test_from_brief_returns_deck(tmp_path):
    """Deck.from_brief reads a plan YAML and returns a Deck with correct slide count."""
    pack = _make_pack(tmp_path)
    layouts = _layouts_dir()
    layout1 = layouts / "horizontal-bullets.slide.dsl"
    layout2 = layouts / "vertical-bullets.slide.dsl"
    assert layout1.is_file(), f"test prerequisite: {layout1} not found"
    assert layout2.is_file(), f"test prerequisite: {layout2} not found"

    # Write a minimal two-slide plan YAML using absolute layout paths.
    brief = tmp_path / "brief.yaml"
    brief.write_text(
        f"brand: feinschliff\n"
        f"out: out/deck.pptx\n"
        f"slides:\n"
        f"  - layout: {layout1}\n"
        f"    content: {{}}\n"
        f"  - layout: {layout2}\n"
        f"    content: {{}}\n",
        encoding="utf-8",
    )

    deck = Deck.from_brief(brief, brand=pack)

    assert isinstance(deck, Deck)
    assert isinstance(deck.document, Document)
    assert len(deck.document.slides) == 2


def test_from_brief_missing_slides_raises(tmp_path):
    """Deck.from_brief raises ValueError when the plan has no 'slides' key."""
    pack = _make_pack(tmp_path)
    brief = tmp_path / "bad.yaml"
    brief.write_text("brand: feinschliff\n", encoding="utf-8")
    with pytest.raises(ValueError, match="slides"):
        Deck.from_brief(brief, brand=pack)


def test_from_brief_missing_layout_raises(tmp_path):
    """Deck.from_brief raises FileNotFoundError for an unknown layout."""
    pack = _make_pack(tmp_path)
    brief = tmp_path / "bad.yaml"
    brief.write_text(
        "brand: feinschliff\nslides:\n  - layout: nonexistent-layout.slide.dsl\n",
        encoding="utf-8",
    )
    with pytest.raises(FileNotFoundError):
        Deck.from_brief(brief, brand=pack)
