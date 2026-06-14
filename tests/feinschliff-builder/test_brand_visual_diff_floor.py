"""Floor-aware visual-diff signal: block vs edge separation + regions.

The struct_diff_ratio scalar counts a 1-2px glyph anti-aliasing halo (the
LibreOffice font-metric floor) identically to a genuinely misplaced block.
These tests prove the morphological split distinguishes the two: a solid
displaced block lands in `block_diff_ratio` (fixable), a thin scattered
halo lands in `edge_diff_ratio` (renderer floor), and regions localise the
block.
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("scipy")

from feinschliff_builder.verify import visual_diff as bvd

H, W = bvd.DESIGN_H, bvd.DESIGN_W


def _blank() -> np.ndarray:
    return np.full((H, W, 3), 255, dtype=np.uint8)


def test_solid_block_classifies_as_block_not_edge():
    """A 200×150 filled block present in render but not source is a
    structural mismatch — it must dominate block_diff_ratio, not edge."""
    src = _blank()
    ren = _blank()
    ren[400:550, 600:800] = 0  # solid black block, well above the open radius

    metrics, _, block_mask = bvd._compute_metrics(src, ren, pic_mask=None)
    assert metrics["block_diff_ratio"] > 0
    # The block is solid, so opening keeps essentially all of it: block is
    # the overwhelming majority of struct, edge is negligible.
    assert metrics["block_diff_ratio"] >= 0.9 * metrics["struct_diff_ratio"]
    assert metrics["edge_diff_ratio"] <= 0.1 * metrics["struct_diff_ratio"]


def test_thin_halo_classifies_as_edge_not_block():
    """Scattered single-pixel diffs (an anti-aliasing halo) are the renderer
    floor — opening removes them, so block_diff_ratio collapses toward 0
    while edge_diff_ratio carries the signal."""
    rng = np.random.default_rng(0)
    src = _blank()
    ren = _blank()
    # 1px-wide diagonal hairlines + sparse speckle: all thinner than the
    # open radius, like glyph-edge anti-aliasing.
    for d in range(0, W, 7):
        ii = np.arange(H)
        jj = (ii + d) % W
        ren[ii, jj] = 0
    speckle = rng.random((H, W)) < 0.01
    ren[speckle] = 0

    metrics, _, _ = bvd._compute_metrics(src, ren, pic_mask=None)
    assert metrics["struct_diff_ratio"] > 0
    # Opening should remove the bulk of the thin halo.
    assert metrics["block_diff_ratio"] < 0.2 * metrics["struct_diff_ratio"]
    assert metrics["edge_diff_ratio"] > metrics["block_diff_ratio"]


def test_block_plus_edge_never_exceeds_struct():
    src = _blank()
    ren = _blank()
    ren[100:300, 100:400] = 0
    ren[::3, ::3] = 0  # add some speckle on top
    metrics, _, _ = bvd._compute_metrics(src, ren, pic_mask=None)
    assert (
        metrics["block_diff_ratio"] + metrics["edge_diff_ratio"]
        <= metrics["struct_diff_ratio"] + 1e-6
    )


def test_regions_localise_the_block():
    src = _blank()
    ren = _blank()
    ren[400:550, 600:800] = 0
    _, _, block_mask = bvd._compute_metrics(src, ren, pic_mask=None)
    regions = bvd._block_regions(block_mask)
    assert regions, "a solid block must produce at least one region"
    top = regions[0]
    cx, cy = top["centroid"]
    assert 600 <= cx <= 800 and 400 <= cy <= 550
    x1, y1, x2, y2 = top["bbox"]
    assert x1 >= 590 and x2 <= 810 and y1 >= 390 and y2 <= 560


def test_clean_render_has_zero_block():
    src = _blank()
    metrics, _, block_mask = bvd._compute_metrics(src, src.copy(), pic_mask=None)
    assert metrics["block_diff_ratio"] == 0.0
    assert metrics["struct_diff_ratio"] == 0.0
    assert bvd._block_regions(block_mask) == []
