"""Unit tests for lib/verify/deck/squint — squint-test thumbnail helper."""
from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from lib.verify.deck.squint import make_squint_thumbnail


def _write_png(path: Path, size: tuple[int, int]) -> Path:
    """Create a simple solid-colour PNG at `path` with the given size."""
    Image.new("RGB", size, color=(180, 200, 220)).save(path, format="PNG")
    return path


def test_downscale_1920x1080_to_25_percent(tmp_path: Path):
    """1920×1080 PNG at default scale 0.25 → 480×270."""
    src = _write_png(tmp_path / "slide.png", (1920, 1080))
    out = tmp_path / "thumb.png"
    result = make_squint_thumbnail(src, out)
    assert result == out
    with Image.open(out) as img:
        assert img.size == (480, 270)


def test_explicit_scale_param(tmp_path: Path):
    """1920×1080 PNG at scale 0.5 → 960×540."""
    src = _write_png(tmp_path / "slide.png", (1920, 1080))
    out = tmp_path / "thumb.png"
    make_squint_thumbnail(src, out, scale=0.5)
    with Image.open(out) as img:
        assert img.size == (960, 540)


def test_output_file_is_created(tmp_path: Path):
    """Output PNG must exist at the requested path after the call."""
    src = _write_png(tmp_path / "slide.png", (800, 600))
    out = tmp_path / "thumb.png"
    assert not out.exists()
    make_squint_thumbnail(src, out)
    assert out.is_file()


def test_missing_source_raises(tmp_path: Path):
    """A non-existent source PNG raises FileNotFoundError."""
    missing = tmp_path / "does_not_exist.png"
    out = tmp_path / "thumb.png"
    with pytest.raises(FileNotFoundError, match="source PNG not found"):
        make_squint_thumbnail(missing, out)
