"""Verify all standalone /excalidraw and /svg fixtures have committed artifacts."""
from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent / "feinschliff"

EXCALIDRAW_FIXTURES = ["auth-flow", "microservices-arch", "user-journey"]
SVG_FIXTURES = ["q1-revenue-breakdown", "feature-adoption-funnel", "stat-card-grid"]


@pytest.mark.parametrize("fixture", EXCALIDRAW_FIXTURES)
def test_excalidraw_fixture_artifacts(fixture):
    base = REPO / "examples" / "excalidraw"
    dsl = base / f"{fixture}.exc.dsl"
    json_ = base / f"{fixture}.excalidraw"
    png = base / f"{fixture}.png"
    if not dsl.exists():
        pytest.skip(f"{fixture}.exc.dsl not yet authored")
    assert json_.exists(), f"{fixture}.excalidraw missing"
    assert png.exists(), f"{fixture}.png missing"
    assert png.stat().st_size > 200, f"{fixture}.png suspiciously small"


@pytest.mark.parametrize("fixture", SVG_FIXTURES)
def test_svg_fixture_artifacts(fixture):
    base = REPO / "examples" / "svg"
    dsl = base / f"{fixture}.svg.dsl"
    svg = base / f"{fixture}.svg"
    png = base / f"{fixture}.png"
    if not dsl.exists():
        pytest.skip(f"{fixture}.svg.dsl not yet authored")
    assert svg.exists(), f"{fixture}.svg missing"
    assert png.exists(), f"{fixture}.png missing"
    assert png.stat().st_size > 200, f"{fixture}.png suspiciously small"
