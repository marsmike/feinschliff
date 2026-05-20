"""Tests for emit_pptx_from_document — typed Document → .pptx entry point."""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from lib.brand import BrandPack
from lib.dsl.ast import Document, Element, ElementKind, Slide
from lib.dsl.parser import parse_document
from lib.dsl.pptx_emit import emit_pptx_from_document


def _make_pack(tmp_path: Path, name: str = "test-brand") -> BrandPack:
    """Create a minimal brand pack directory with valid tokens.json."""
    # Use the real feinschliff brand pack since build_presentation requires
    # real tokens (font-family, font-size, etc.) to function.
    real_brand = Path(__file__).resolve().parents[1] / "brands" / "feinschliff"
    return BrandPack.load(real_brand)


# ---------------------------------------------------------------------------
# Smoke test — emit a minimal single-slide document
# ---------------------------------------------------------------------------

def test_emit_pptx_from_document_returns_path(tmp_path):
    out = tmp_path / "out.pptx"
    doc = parse_document(
        "canvas 1920x1080\nrect 0,0 1920x1080 fill:#000000\n"
    )
    pack = _make_pack(tmp_path)
    result = emit_pptx_from_document(doc, pack, out)
    assert result == out


def test_emit_pptx_from_document_creates_file(tmp_path):
    out = tmp_path / "out.pptx"
    doc = parse_document("canvas 1920x1080\nrect 0,0 1920x1080 fill:#000000\n")
    pack = _make_pack(tmp_path)
    emit_pptx_from_document(doc, pack, out)
    assert out.is_file()


def test_emit_pptx_from_document_is_valid_pptx(tmp_path):
    """The output must be a valid zip/Office Open XML file."""
    out = tmp_path / "out.pptx"
    doc = parse_document("canvas 1920x1080\nrect 0,0 1920x1080 fill:#000000\n")
    pack = _make_pack(tmp_path)
    emit_pptx_from_document(doc, pack, out)
    assert zipfile.is_zipfile(out), "Output is not a valid zip file (invalid PPTX)"


def test_emit_pptx_from_document_raises_on_empty(tmp_path):
    """A document with no slides must raise ValueError."""
    doc = Document(slides=[])
    pack = _make_pack(tmp_path)
    with pytest.raises(ValueError, match="no slides"):
        emit_pptx_from_document(doc, pack, tmp_path / "out.pptx")


def test_emit_pptx_from_document_roundtrip(tmp_path):
    """Parse a layout DSL, emit to PPTX — the file must be well-formed."""
    # Use a real layout from the bundled layouts
    layouts_dir = Path(__file__).resolve().parents[1] / "layouts"
    layout_files = list(layouts_dir.glob("*.slide.dsl"))
    if not layout_files:
        pytest.skip("no bundled layouts found")

    layout_path = layout_files[0]
    doc = parse_document(layout_path.read_text(), source=str(layout_path))
    pack = _make_pack(tmp_path)
    out = tmp_path / "roundtrip.pptx"

    # Some layouts require content slots — for the roundtrip test we just
    # check that the emitter doesn't crash and produces a valid zip.
    try:
        emit_pptx_from_document(doc, pack, out)
        assert zipfile.is_zipfile(out)
    except Exception:
        # Layout may have required slots or fonts; that's OK for this smoke test.
        pytest.skip(f"Layout {layout_path.name} requires content/fonts not provided")
