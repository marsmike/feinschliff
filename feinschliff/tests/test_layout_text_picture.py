"""Regression: text-picture's fixture must reference an actual image.

Before 2026-05-15 `tests/fixtures/layouts/text-picture.yaml` had
`image: ""`. The text-picture slide title shipped as "Text paired with
a picture" but the picture column rendered as an empty placeholder
rect — the showcase build bypassed the `MISSING_ASSET` rule via
`--allow-missing-assets` (a blanket flag the showcase script uses
because some layouts legitimately have empty optional pictures).

The fix wires the fixture's `image:` slot to an illustration that
exists on disk — currently the shared `illustrations/placeholder.jpg`
at the plugin-level assets root, resolved via the asset fallback chain
(brand-specific override wins; plugin default kicks in otherwise).
This test ensures the fixture keeps pointing at an image that actually
exists on disk in either location regardless of which specific asset
is chosen.

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
# Asset resolution walks brand-specific assets first, then falls back to
# the plugin-level shared assets dir (see cli/build.py + lib/dsl/pptx_emit
# `asset_root_fallback`). The fixture's `image:` may resolve at either.
BRAND_ASSETS = REPO / "brands" / "feinschliff" / "assets"
PLUGIN_ASSETS = REPO / "assets"


def test_text_picture_fixture_references_an_image():
    data = yaml.safe_load(FIXTURE.read_text())
    image = data.get("image", "")
    assert image, (
        f"text-picture fixture has empty `image:` — the layout's whole "
        f"purpose is the picture frame, so a blank slot defeats the showcase"
    )


def test_text_picture_referenced_image_exists_on_disk():
    """The referenced path resolves under the brand assets dir OR the
    plugin-level fallback assets dir (see `EmitContext.asset_root_fallback`).
    """
    data = yaml.safe_load(FIXTURE.read_text())
    image = data.get("image", "")
    if not image:
        return  # other test covers this
    brand_path = BRAND_ASSETS / image
    plugin_path = PLUGIN_ASSETS / image
    assert brand_path.is_file() or plugin_path.is_file(), (
        f"text-picture image `{image}` not found at {brand_path} "
        f"nor at {plugin_path}"
    )
