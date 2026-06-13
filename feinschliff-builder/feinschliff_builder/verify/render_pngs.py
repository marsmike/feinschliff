"""Render each slide of a .pptx to a PNG. Best-effort."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def render_slides_to_png(deck: Path, out_dir: Path) -> dict[int, Path]:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        print(
            "WARN: soffice/libreoffice not found on PATH — "
            "skipping PNG render; squint rubric will be empty",
            file=sys.stderr,
        )
        return {}
    # Reuse the canonical converter — it isolates each call with its own
    # `UserInstallation` profile so parallel verify runs don't collide on the
    # shared soffice profile lock (and silently produce no PDF).
    from feinschliff.io.soffice import pptx_to_pdf

    try:
        pdf = pptx_to_pdf(deck, out_dir)
    except RuntimeError as e:
        print(f"WARN: soffice pdf conversion failed: {e}", file=sys.stderr)
        return {}
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        print(
            "WARN: pdftoppm not found on PATH — "
            "skipping PNG rasterisation; squint rubric will be empty",
            file=sys.stderr,
        )
        return {}
    subprocess.check_call([
        pdftoppm, "-r", "144", "-png", str(pdf), str(out_dir / "slide"),
    ])
    # Filter to numerically-suffixed pages only: pdftoppm names its
    # output `slide-N.png` (1-based) but the same out_dir may already
    # carry a `slide-thumb.png` from an earlier render step, which then
    # crashed the int() parse.
    out: dict[int, Path] = {}
    for p in sorted(out_dir.glob("slide-*.png")):
        suffix = p.stem.rsplit("-", 1)[-1]
        if suffix.isdigit():
            out[int(suffix)] = p
    return out
