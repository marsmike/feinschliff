"""Render each slide of a .pptx to a PNG. Best-effort."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def render_slides_to_png(deck: Path, out_dir: Path) -> dict[int, Path]:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        return {}
    pdf = out_dir / (deck.stem + ".pdf")
    subprocess.check_call([
        soffice, "--headless", "--convert-to", "pdf",
        "--outdir", str(out_dir), str(deck),
    ])
    if not pdf.exists():
        return {}
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        return {}
    subprocess.check_call([
        pdftoppm, "-r", "144", "-png", str(pdf), str(out_dir / "slide"),
    ])
    return {
        int(p.stem.rsplit("-", 1)[-1]): p
        for p in sorted(out_dir.glob("slide-*.png"))
    }
