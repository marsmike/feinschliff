"""`chars` front-matter budgets must come from real metrics at the pack's real
scale — not 0.55em × CSS 96/72 with a 1-row floor (R4)."""
import math

import pytest

from feinschliff_builder.decompile.layout_profile_gen import _char_capacity
from feinschmiede.text import measure


def _require_font():
    if measure.find_font_file("DejaVu Sans") is None:
        pytest.skip("DejaVu Sans not resolvable")


def test_zero_rows_is_honest_zero():
    """Box shorter than one line → 0 chars, no max(1, rows) lie."""
    slot = {"pt": 16.0, "maxw": 300.0, "maxh": 27.0, "style": ""}
    assert _char_capacity(slot, px_per_pt=2.2229) == 0


def test_capacity_within_15pct_of_pil_truth():
    """±15% of a PIL greedy-wrap ground truth on a representative slot."""
    _require_font()
    from PIL import ImageFont
    px_per_pt = 2.2229
    slot = {"pt": 16.0, "maxw": 920.0, "maxh": 787.0, "style": ""}

    path = measure.find_font_file("DejaVu Sans")
    size_px = slot["pt"] * px_per_pt
    probe = 100.0
    font = ImageFont.truetype(str(path), int(probe))
    words = ("revenue growth margin pipeline churn uplift retention onboarding "
             "expansion forecast quarter enterprise customers benchmark velocity").split()
    max_lines = math.floor(slot["maxh"] / (size_px * 1.2))
    placed, line, i = [], "", 0
    while True:
        word = words[i % len(words)]
        i += 1
        cand = word if not line else f"{line} {word}"
        if font.getlength(cand) * (size_px / probe) <= slot["maxw"]:
            line = cand
            continue
        placed.append(line)
        if len(placed) >= max_lines:
            break
        line = word
    truth = len(" ".join(placed))

    # Face comes through tokens in production; pass it directly here.
    cap = _char_capacity(slot, px_per_pt=px_per_pt, face="DejaVu Sans")
    assert abs(cap - truth) <= 0.15 * truth, f"chars={cap} vs PIL truth={truth}"
