"""WCAG palette safety: verify each brand has at least one readable text-on-paper combo.

Body-text legibility varies by brand convention — feinschliff renders body in
`ink`, dark-first brands like binance render body in `black` (semantically
inverted). Rather than fix on one slot, this test picks the BEST text-candidate
for each brand from a small set and asserts that pair clears WCAG AA Large.

The accent slot is treated separately and given a low bar (2.0:1) because
brand accents are often decorative-only and intentionally low-contrast
(e.g. Feinschliff's gold on cream sits at 2.26:1 by design).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from feinschliff.design_md import parse as parse_design_md  # noqa: E402


def _local_brands() -> list[str]:
    """Brand names from THIS repo's `brands/` only — ignore plugin caches and
    user sideloads so the test is hermetic to the working tree."""
    brands_dir = REPO_ROOT / "brands"
    return sorted(p.name for p in brands_dir.iterdir()
                  if p.is_dir() and (p / "DESIGN.md").is_file())

# Slots that conventionally render body / display text. Dark-first brands flip
# `black` to be soft-white so we test all of them and pick the highest-contrast.
TEXT_CANDIDATES = ("ink", "black", "graphite", "off-white")


def _hex_to_rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0)


def _luminance(h: str) -> float:
    """Relative luminance per WCAG 2.x — sRGB → linear → weighted sum."""
    r, g, b = _hex_to_rgb(h)
    def _lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast_ratio(fg: str, bg: str) -> float:
    l1, l2 = _luminance(fg), _luminance(bg)
    lighter, darker = (l1, l2) if l1 > l2 else (l2, l1)
    return (lighter + 0.05) / (darker + 0.05)


@pytest.mark.parametrize("brand", _local_brands())
def test_at_least_one_text_slot_meets_wcag_aa_large_on_paper(brand):
    """For each brand, the best text-candidate vs paper must clear AA Large (3.0:1)."""
    dm = parse_design_md(REPO_ROOT / "brands" / brand / "DESIGN.md")
    if "paper" not in dm.colors:
        pytest.skip(f"{brand}: missing paper slot in DESIGN.md")
    paper = dm.colors["paper"]
    candidates = {slot: dm.colors[slot] for slot in TEXT_CANDIDATES if slot in dm.colors}
    if not candidates:
        pytest.skip(f"{brand}: no text-candidate slots present")
    ratios = {slot: contrast_ratio(hx, paper) for slot, hx in candidates.items()}
    best_slot = max(ratios, key=ratios.get)
    best_ratio = ratios[best_slot]
    assert best_ratio >= 3.0, (
        f"{brand}: no text slot reads on paper ({paper}). "
        f"Best candidate: {best_slot} ({candidates[best_slot]}) "
        f"at {best_ratio:.2f}:1 (WCAG AA Large needs 3.0:1)\n"
        f"All candidates: " + ", ".join(f"{s}={r:.2f}" for s, r in ratios.items())
    )


@pytest.mark.parametrize("brand", _local_brands())
def test_accent_on_paper_visible(brand):
    """Accent on paper must clear a 2.0:1 floor — visible-as-decoration, not necessarily text."""
    dm = parse_design_md(REPO_ROOT / "brands" / brand / "DESIGN.md")
    if "accent" not in dm.colors or "paper" not in dm.colors:
        pytest.skip(f"{brand}: missing accent or paper slot in DESIGN.md")
    ratio = contrast_ratio(dm.colors["accent"], dm.colors["paper"])
    assert ratio >= 2.0, (
        f"{brand}: accent ({dm.colors['accent']}) is invisible on paper "
        f"({dm.colors['paper']}) at {ratio:.2f}:1 (need 2.0:1 even for decoration)"
    )
