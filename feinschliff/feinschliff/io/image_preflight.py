"""Deterministic image preflight: palette-clash + crop-risk scoring.

Replaces roughly half of LLM image-quality judgements with fast,
reproducible checks that run before a picture is inserted into a slide.
No external dependencies beyond Pillow — sRGB→Lab is implemented inline.

Public surface
--------------
``score_image(img, brand_palette_hex, target_aspect) -> ImageScore``
    Pure scorer: returns normalised palette_clash / crop_risk scalars plus
    the top-3 dominant colours and the image's aspect ratio.

``preflight_image(img, brand_palette_hex, slot_aspect, *, slide_index, thresholds) -> (ImageScore, list[Defect])``
    Scorer + defect emitter. Fires IMAGE_PALETTE_CLASH / IMAGE_CROP_RISK
    against configurable thresholds (defaults: 0.60 and 0.50 respectively).

Both are deterministic and side-effect-free.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PIL import Image

from feinschliff.defects import Defect, DefectKind, Severity

if TYPE_CHECKING:
    pass  # avoid circular at type-check time


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ImageScore:
    """Scores for one image against a brand palette and a target slot.

    All float fields are clamped to [0.0, 1.0] at construction time.
    """
    palette_clash: float        # 0.0 = brand-aligned, 1.0 = clashes
    crop_risk: float            # 0.0 = safe, 1.0 = subject likely cropped
    dominant_hex: list[str]     # top-3 dominant #rrggbb strings
    aspect_ratio: float         # image_width / image_height


# ---------------------------------------------------------------------------
# Colour helpers (no external deps)
# ---------------------------------------------------------------------------

def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Parse '#FFAA00' or 'FFAA00' (any case) → (255, 170, 0)."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"expected 6-digit hex, got {hex_color!r}")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _srgb_to_linear(c: float) -> float:
    """sRGB gamma → linear light, for one channel in [0, 1]."""
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _rgb_to_lab(r: int, g: int, b: int) -> tuple[float, float, float]:
    """Convert integer sRGB (0..255) to CIE L*a*b* (D65 illuminant).

    Implements the standard sRGB → XYZ (D65) → Lab chain.
    The sRGB primaries + D65 matrix comes from IEC 61966-2-1.
    """
    # 1. sRGB → linear light [0, 1]
    rl = _srgb_to_linear(r / 255.0)
    gl = _srgb_to_linear(g / 255.0)
    bl = _srgb_to_linear(b / 255.0)

    # 2. Linear sRGB → CIE XYZ (D65) via the standard 3×3 matrix
    x = rl * 0.4124564 + gl * 0.3575761 + bl * 0.1804375
    y = rl * 0.2126729 + gl * 0.7151522 + bl * 0.0721750
    z = rl * 0.0193339 + gl * 0.1191920 + bl * 0.9503041

    # 3. Normalise by D65 white point
    xn, yn, zn = 0.95047, 1.00000, 1.08883
    fx = _f_lab(x / xn)
    fy = _f_lab(y / yn)
    fz = _f_lab(z / zn)

    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b_val = 200.0 * (fy - fz)
    return L, a, b_val


def _f_lab(t: float) -> float:
    """CIE Lab cube-root function with linear segment for small values."""
    if t > 0.008856:
        return t ** (1.0 / 3.0)
    return 7.787 * t + 16.0 / 116.0


def _delta_e_cie76(
    r1: int, g1: int, b1: int,
    r2: int, g2: int, b2: int,
) -> float:
    """CIE76 ΔE between two sRGB colours: sqrt(ΔL² + Δa² + Δb²)."""
    l1, a1, b1_ = _rgb_to_lab(r1, g1, b1)
    l2, a2, b2_ = _rgb_to_lab(r2, g2, b2)
    return math.sqrt((l1 - l2) ** 2 + (a1 - a2) ** 2 + (b1_ - b2_) ** 2)


# ---------------------------------------------------------------------------
# Dominant-colour extraction
# ---------------------------------------------------------------------------

def _is_near_black_or_white(r: int, g: int, b: int, threshold: int = 15) -> bool:
    """True when the colour is perceptually black or white."""
    return (
        (r < threshold and g < threshold and b < threshold)
        or (r > 255 - threshold and g > 255 - threshold and b > 255 - threshold)
    )


def _extract_dominant_colors(img: Image.Image, n: int = 3) -> list[tuple[int, int, int]]:
    """Return the top-``n`` dominant RGB triples from ``img``.

    Strategy:
    1. Convert to RGB (drops alpha / expands grayscale).
    2. Quantize to 16 colours (Pillow median-cut).
    3. Retrieve the palette + per-palette-index pixel counts.
    4. Sort by count descending; skip entries where the colour is
       "near-black" or "near-white" and that entry accounts for >90%
       of total pixels (typical watermark / pure-background signal).
    5. Return up to ``n`` triples.

    If all colours are near-black/white, skip the filter so the caller
    always gets at least one result.
    """
    rgb_img = img.convert("RGB")
    total_pixels = rgb_img.width * rgb_img.height

    # Quantize to 16 colours and collect (count, palette_index) pairs.
    # PIL getcolors() returns (count, value) tuples — value is the palette
    # index for mode-P images.
    q = rgb_img.quantize(colors=16, dither=Image.Dither.NONE)
    counts: dict[int, int] = {}
    for count, palette_idx in (q.getcolors(maxcolors=q.width * q.height) or []):
        counts[palette_idx] = count

    # Build a list of (count, r, g, b) sorted by count descending.
    palette_bytes = q.getpalette() or []
    entries: list[tuple[int, int, int, int]] = []  # (count, r, g, b)
    for idx, cnt in counts.items():
        if idx * 3 + 2 >= len(palette_bytes):
            continue
        r, g, b = palette_bytes[idx * 3], palette_bytes[idx * 3 + 1], palette_bytes[idx * 3 + 2]
        entries.append((cnt, r, g, b))
    entries.sort(reverse=True)

    # Filter out near-black/white entries that dominate >90% of pixels,
    # but only if there's at least one coloured entry remaining.
    filtered = [
        (cnt, r, g, b) for cnt, r, g, b in entries
        if not (_is_near_black_or_white(r, g, b) and cnt / total_pixels > 0.90)
    ]
    if not filtered:
        filtered = entries  # fallback: return all colours

    return [(r, g, b) for _, r, g, b in filtered[:n]]


# ---------------------------------------------------------------------------
# Palette-clash scoring
# ---------------------------------------------------------------------------

def _palette_clash_score(
    dominant: list[tuple[int, int, int]],
    brand_palette_hex: list[str],
) -> float:
    """Compute palette_clash ∈ [0.0, 1.0].

    For the image's dominant colour (first in ``dominant``), find the
    minimum CIE76 ΔE to any brand-palette colour. Normalise:
      ΔE 0..10  → 0.0 (visually identical to a brand colour)
      ΔE 10..30 → linear ramp
      ΔE > 30   → 1.0 (clearly clashes)
    """
    if not dominant or not brand_palette_hex:
        return 0.0

    dr, dg, db = dominant[0]

    min_de: float = math.inf
    for hex_color in brand_palette_hex:
        try:
            br, bg, bb = _hex_to_rgb(hex_color)
        except ValueError:
            continue
        de = _delta_e_cie76(dr, dg, db, br, bg, bb)
        if de < min_de:
            min_de = de

    if min_de == math.inf:
        return 0.0

    # Normalise ΔE to [0, 1]
    if min_de <= 10.0:
        return 0.0
    if min_de >= 30.0:
        return 1.0
    return (min_de - 10.0) / 20.0


# ---------------------------------------------------------------------------
# Crop-risk scoring
# ---------------------------------------------------------------------------

def _crop_risk_score(image_aspect: float, target_aspect: float) -> float:
    """Compute crop_risk ∈ [0.0, 1.0].

    ratio = |image_aspect - target_aspect| / max(image_aspect, target_aspect)
      ratio < 0.15  → 0.0 (safe)
      0.15 ≤ ratio ≤ 0.40 → linear ramp
      ratio > 0.40  → 1.0 (high crop risk)
    """
    if target_aspect <= 0 or image_aspect <= 0:
        return 0.0
    ratio = abs(image_aspect - target_aspect) / max(image_aspect, target_aspect)
    if ratio < 0.15:
        return 0.0
    if ratio > 0.40:
        return 1.0
    return (ratio - 0.15) / 0.25


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_image(
    img: Image.Image,
    brand_palette_hex: list[str],
    target_aspect: float,
) -> ImageScore:
    """Compute a deterministic ImageScore for one image.

    Parameters
    ----------
    img:
        Any PIL Image. Converted to RGB internally.
    brand_palette_hex:
        Brand colour tokens as ``#rrggbb`` strings (any case, leading ``#``
        optional). Passed to the palette-clash scorer.
    target_aspect:
        The slot's desired aspect ratio (width / height). Used by the
        crop-risk scorer.

    Returns
    -------
    ImageScore
        Frozen dataclass with ``palette_clash``, ``crop_risk``,
        ``dominant_hex`` (up to 3), and ``aspect_ratio``.
    """
    rgb_img = img.convert("RGB")
    image_aspect = rgb_img.width / rgb_img.height

    dominant = _extract_dominant_colors(rgb_img, n=3)

    clash = _palette_clash_score(dominant, brand_palette_hex)
    risk = _crop_risk_score(image_aspect, target_aspect)

    dominant_hex = [f"#{r:02x}{g:02x}{b:02x}" for r, g, b in dominant]

    return ImageScore(
        palette_clash=max(0.0, min(1.0, clash)),
        crop_risk=max(0.0, min(1.0, risk)),
        dominant_hex=dominant_hex,
        aspect_ratio=image_aspect,
    )


_DEFAULT_THRESHOLDS: dict[str, float] = {
    "palette_clash": 0.60,
    "crop_risk": 0.50,
}


def preflight_image(
    img: Image.Image,
    brand_palette_hex: list[str],
    slot_aspect: float,
    *,
    slide_index: int,
    thresholds: dict[str, float] | None = None,
) -> tuple[ImageScore, list[Defect]]:
    """Score ``img`` and emit :class:`~feinschliff.defects.Defect` records.

    Parameters
    ----------
    img:
        Image to evaluate. Any Pillow mode; converted internally to RGB.
    brand_palette_hex:
        Brand colours as ``#rrggbb`` hex strings.
    slot_aspect:
        Target slot aspect ratio (width / height).
    slide_index:
        Slide index for the emitted defects.
    thresholds:
        Override default decision thresholds. Recognised keys:
        ``"palette_clash"`` (default 0.60) and ``"crop_risk"``
        (default 0.50). Values above the threshold fire a WARN defect.

    Returns
    -------
    (ImageScore, list[Defect])
        The score plus any defects (may be empty).
    """
    t = {**_DEFAULT_THRESHOLDS, **(thresholds or {})}
    score = score_image(img, brand_palette_hex, slot_aspect)
    defects: list[Defect] = []

    if score.palette_clash > t["palette_clash"]:
        defects.append(Defect(
            slide_index=slide_index,
            kind=DefectKind.IMAGE_PALETTE_CLASH,
            severity=Severity.WARN,
            message=(
                f"dominant image colour clashes with brand palette "
                f"(palette_clash={score.palette_clash:.2f}, "
                f"threshold={t['palette_clash']:.2f})"
            ),
            meta={"palette_clash": score.palette_clash, "dominant_hex": score.dominant_hex},
        ))

    if score.crop_risk > t["crop_risk"]:
        defects.append(Defect(
            slide_index=slide_index,
            kind=DefectKind.IMAGE_CROP_RISK,
            severity=Severity.WARN,
            message=(
                f"image aspect ({score.aspect_ratio:.2f}) differs from slot "
                f"({slot_aspect:.2f}); subject may be cropped "
                f"(crop_risk={score.crop_risk:.2f}, "
                f"threshold={t['crop_risk']:.2f})"
            ),
            meta={"crop_risk": score.crop_risk, "aspect_ratio": score.aspect_ratio,
                  "slot_aspect": slot_aspect},
        ))

    return score, defects


__all__ = ["ImageScore", "score_image", "preflight_image"]
