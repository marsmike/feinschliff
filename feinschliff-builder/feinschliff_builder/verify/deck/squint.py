"""Squint-test thumbnail helper — visual verify class.

Render a slide PNG at 25% scale (default), let the LLM step back and judge
whether the headline message is still legible at thumbnail size. Catches
visually noisy slides that pass per-element checks but fail "step back and
read it" tests — the visual hierarchy collapses or the slide reads as a
wall of small things.

This module ships only the deterministic part: thumbnail generation. The
LLM judgment runs at step 4 verify (see
`skills/deck/references/iteration-loop.md` defect class squint-test, #23).
"""
from __future__ import annotations

from pathlib import Path


def make_squint_thumbnail(
    source_png: Path,
    output_png: Path,
    *,
    scale: float = 0.25,
) -> Path:
    """Resize source_png to `scale` × original dimensions, save as output_png.

    Returns the output_png path. Uses Pillow (PIL) — already a dep via
    feinschliff/lib/dsl/pptx_emit.py's picture_treatment code path. Box
    sampling (default in Pillow's resize) is appropriate for downsampling.
    """
    from PIL import Image

    if not source_png.is_file():
        raise FileNotFoundError(f"source PNG not found: {source_png}")

    with Image.open(source_png) as img:
        new_w = max(1, int(round(img.width * scale)))
        new_h = max(1, int(round(img.height * scale)))
        thumb = img.resize((new_w, new_h), Image.Resampling.BOX)
        thumb.save(output_png, format="PNG")

    return output_png
