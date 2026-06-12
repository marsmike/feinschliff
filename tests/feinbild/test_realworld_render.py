"""Durable real-world end-to-end tests for the diagram pipeline.

DSL -> expanded doc -> rendered PNG via the production rough+cairosvg backend.
Skipped automatically when cairosvg / libcairo2 is unavailable.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from feinbild import diagrams_cli

BRAND = "feinschliff"

SKILLS_DIR = Path(__file__).resolve().parents[2] / "feinbild" / "skills"
SVG_DSL = SKILLS_DIR / "svg" / "examples" / "yocto-build-pipeline.svg.dsl"
EXC_DSL = SKILLS_DIR / "excalidraw" / "examples" / "ota-update-simple-pupil.exc.dsl"


def _require_cairo() -> None:
    """Skip the test when cairosvg or libcairo2 is not available."""
    try:
        import cairosvg  # noqa: F401
    except ImportError:
        pytest.skip("cairosvg not installed")
    except OSError as exc:
        pytest.skip(f"cairosvg native library unavailable: {exc}")


def test_svg_dsl_expand_and_render(tmp_path: Path) -> None:
    _require_cairo()
    expanded = tmp_path / "yocto-build-pipeline.svg"
    png = tmp_path / "yocto-build-pipeline.png"

    assert diagrams_cli.cmd_svg_expand(SVG_DSL, expanded, brand=BRAND) == 0
    assert expanded.exists()
    assert expanded.read_text().startswith("<?xml")

    assert diagrams_cli.cmd_render(expanded, png) == 0
    assert png.exists()

    from PIL import Image
    img = Image.open(png)
    assert img.format == "PNG"
    assert img.width > 50
    assert img.height > 50


def test_excalidraw_dsl_expand_and_render(tmp_path: Path) -> None:
    _require_cairo()
    expanded = tmp_path / "ota-update-simple-pupil.excalidraw"
    png = tmp_path / "ota-update-simple-pupil.png"

    assert diagrams_cli.cmd_excalidraw_expand(EXC_DSL, expanded, brand=BRAND) == 0
    assert expanded.exists()
    assert expanded.read_text().startswith("{")

    assert diagrams_cli.cmd_render(expanded, png) == 0
    assert png.exists()

    from PIL import Image
    img = Image.open(png)
    assert img.format == "PNG"
    assert img.width > 50
    assert img.height > 50
