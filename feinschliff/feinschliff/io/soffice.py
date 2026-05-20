"""Shared LibreOffice pptx → pdf / png helpers for the render scripts.

Centralises the `soffice --headless --convert-to pdf` invocation with
isolated `UserInstallation` profiles — parallel callers would otherwise
collide on the shared profile lock and silently produce no output — plus
the `pdftoppm` rasterise step most callers do next.

Five scripts (render_v2_goldens, dsl_golden_compare, render_brand_atlas,
render_brand_preview, render_side_by_side) each had their own copy of
this dance; this module is the single canonical version.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


SOFFICE = shutil.which("soffice") or "/opt/homebrew/bin/soffice"
PDFTOPPM = shutil.which("pdftoppm") or "/opt/homebrew/bin/pdftoppm"


def pptx_to_pdf(pptx_path: Path, out_dir: Path) -> Path:
    """Convert .pptx → .pdf via soffice; return the PDF path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="soffice-profile-") as profile:
        try:
            subprocess.run(
                [SOFFICE, f"-env:UserInstallation=file://{profile}",
                 "--headless", "--convert-to", "pdf",
                 "--outdir", str(out_dir), str(pptx_path)],
                check=True, capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            stderr_text = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
            raise RuntimeError(f"soffice failed: {stderr_text[:500]}") from e
    pdf = out_dir / pptx_path.with_suffix(".pdf").name
    if not pdf.is_file():
        raise RuntimeError(f"soffice produced no PDF for {pptx_path}")
    return pdf


def pptx_to_png(pptx_path: Path, out_dir: Path,
                *, slide_index: int | None = None, dpi: int = 96,
                prefix: str = "page") -> Path:
    """Convert .pptx → PNG; return the first matching PNG path.

    `slide_index` is 1-based; when None, every slide is rasterised and
    the first PNG is returned (the legacy "page-1.png" behaviour). The
    PDF intermediate lands next to the PNGs inside `out_dir`. `prefix`
    controls the pdftoppm output stem — set it per-call when multiple
    pptxs share an `out_dir` and you need stable, distinct PNG names.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf = pptx_to_pdf(pptx_path, out_dir)
    cmd = [PDFTOPPM, "-r", str(dpi), "-png"]
    if slide_index is not None:
        cmd += ["-f", str(slide_index), "-l", str(slide_index)]
    cmd += [str(pdf), str(out_dir / prefix)]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        stderr_text = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        raise RuntimeError(f"soffice failed: {stderr_text[:500]}") from e
    pngs = sorted(out_dir.glob(f"{prefix}-*.png"))
    if not pngs:
        raise RuntimeError(f"pdftoppm produced no PNG for {pptx_path}")
    return pngs[0]
