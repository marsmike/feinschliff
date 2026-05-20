"""Tests for `lib.verify.deck.thumbnails_grid.render_thumbnails_grid_pdf`.

PIL-only implementation — no reportlab. Verifies multi-page composition,
non-empty output, single-page fallback, and nested-output-dir creation.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from lib.verify.deck.thumbnails_grid import render_thumbnails_grid_pdf


_COLOR_PALETTE = [
    (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
    (255, 0, 255), (0, 255, 255), (128, 0, 0), (0, 128, 0),
    (0, 0, 128), (128, 128, 0), (128, 0, 128), (0, 128, 128),
    (200, 200, 200), (100, 100, 100), (255, 128, 0), (128, 255, 0),
    (0, 255, 128), (128, 0, 255), (255, 0, 128), (0, 128, 255),
]


def _make_pngs(tmp_path: Path, n: int) -> list[Path]:
    """Generate `n` 200x150 solid-color PNGs and return their paths."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for i in range(n):
        color = _COLOR_PALETTE[i % len(_COLOR_PALETTE)]
        img = Image.new("RGB", (200, 150), color=color)
        p = tmp_path / f"slide_{i:03d}.png"
        img.save(p, format="PNG")
        paths.append(p)
    return paths


def test_12_thumbs_one_page_pdf(tmp_path: Path):
    pngs = _make_pngs(tmp_path, 12)
    out = tmp_path / "grid.pdf"
    result = render_thumbnails_grid_pdf(pngs, out)
    assert result == out
    assert out.is_file()
    assert out.stat().st_size > 0
    # PDF magic bytes.
    assert out.read_bytes()[:4] == b"%PDF"


def test_3_thumbs_single_page_still_produces_pdf(tmp_path: Path):
    pngs = _make_pngs(tmp_path, 3)
    out = tmp_path / "grid.pdf"
    render_thumbnails_grid_pdf(pngs, out)
    assert out.is_file()
    assert out.stat().st_size > 0
    assert out.read_bytes()[:4] == b"%PDF"


def test_20_thumbs_multi_page_pdf_non_zero(tmp_path: Path):
    # Default grid is 4×4 = 16 cells/page → 20 thumbs → 2 pages.
    pngs = _make_pngs(tmp_path, 20)
    out = tmp_path / "grid.pdf"
    render_thumbnails_grid_pdf(pngs, out)
    assert out.is_file()
    size_20 = out.stat().st_size
    assert size_20 > 0
    # A smaller 8-thumb (single-page) output should be strictly smaller
    # than the 20-thumb (2-page) one — sanity check that pages actually
    # got added, not just that the same single page got rewritten.
    pngs_small = _make_pngs(tmp_path / "small", 8)
    out_small = tmp_path / "grid_small.pdf"
    render_thumbnails_grid_pdf(pngs_small, out_small)
    assert out_small.stat().st_size > 0
    assert size_20 > out_small.stat().st_size


def test_nested_output_dir_is_created(tmp_path: Path):
    pngs = _make_pngs(tmp_path, 4)
    nested = tmp_path / "a" / "b" / "c" / "grid.pdf"
    assert not nested.parent.exists()
    render_thumbnails_grid_pdf(pngs, nested)
    assert nested.is_file()
    assert nested.stat().st_size > 0


def test_empty_png_list_raises(tmp_path: Path):
    with pytest.raises(ValueError):
        render_thumbnails_grid_pdf([], tmp_path / "grid.pdf")
