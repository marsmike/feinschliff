"""Regression: text-picture's fixture must reference an actual image.

Before 2026-05-15 `tests/fixtures/layouts/text-picture.yaml` had
`image: ""`. The text-picture slide title shipped as "Text paired with
a picture" but the picture column rendered as an empty placeholder
rect — the showcase build bypassed the `MISSING_ASSET` rule via
`--allow-missing-assets` (a blanket flag the showcase script uses
because some layouts legitimately have empty optional pictures).

The fix wires the fixture's `image:` slot to a brand illustration
that exists on disk (currently `illustrations/feinschliff-craft.jpg`,
originally `illustrations/folie20-people.png`). This test ensures the
fixture keeps pointing at an image that actually exists on disk
regardless of which specific asset is chosen.

Diagnosis note: `MISSING_ASSET` is in `_FATAL` per `lib/defects.py`,
but `render_brand_preview.py` (the showcase builder) passes
`--allow-missing-assets`, which is why this defect shipped. Long term,
we should require image slots to be non-empty for layouts whose
purpose hinges on the image (text-picture, full-bleed-cover) — opt in
via per-fixture metadata rather than blanket suppression.
"""
from __future__ import annotations

from pathlib import Path

import yaml


REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "layouts" / "text-picture.yaml"
BRAND_ASSETS = REPO / "brands" / "feinschliff" / "assets"


def test_text_picture_fixture_references_an_image():
    data = yaml.safe_load(FIXTURE.read_text())
    image = data.get("image", "")
    assert image, (
        f"text-picture fixture has empty `image:` — the layout's whole "
        f"purpose is the picture frame, so a blank slot defeats the showcase"
    )


def test_text_picture_referenced_image_exists_on_disk():
    """The referenced path is relative to `brands/<brand>/assets`."""
    data = yaml.safe_load(FIXTURE.read_text())
    image = data.get("image", "")
    if not image:
        return  # other test covers this
    asset_path = BRAND_ASSETS / image
    assert asset_path.is_file(), (
        f"text-picture image `{image}` not found at {asset_path}"
    )
