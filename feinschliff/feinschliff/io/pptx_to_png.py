"""PPTX → PNG rasterizer via LibreOffice headless.

Used by the wireframe overlay mode to embed the actual rendered slide
behind the DSL bounding boxes so deviations are immediately visible.

LibreOffice is the system-level dependency (``libreoffice --headless``).
All work is done in a temp directory; callers receive base64-encoded PNG
strings suitable for embedding in SVG ``<image href="data:image/png;base64,..."/>``.

**Multi-slide limitation**: LibreOffice ``--convert-to png`` behaviour varies
by version. Many releases only rasterize the *first* slide of a PPTX file,
producing a single ``<stem>.png`` regardless of slide count. The
``_collect_output_pngs`` helper handles both the single-file naming scheme
and the numbered multi-slide scheme (``<stem>1.png``, ``<stem>2.png``, …)
used by some LO versions. If your LibreOffice only exports one slide, the
returned list will contain a single entry; callers that expect one PNG per
slide (e.g. ``wireframe-sheet --overlay-pptx``) will emit a warning.

Usage::

    from feinschliff.io.pptx_to_png import pptx_to_pngs_b64, slide_to_b64

    b64_list = pptx_to_pngs_b64(Path("deck.pptx"))   # one entry per slide exported
    b64 = slide_to_b64(Path("deck.pptx"), slide_index=0)
"""
from __future__ import annotations

import base64
import shutil
import subprocess
import tempfile
from pathlib import Path


def pptx_to_pngs_b64(
    pptx_path: Path,
    *,
    timeout: int = 60,
) -> list[str]:
    """Rasterize every slide in *pptx_path* to PNG via LibreOffice.

    Returns a list of base64-encoded PNG strings, one per slide, in slide
    order. Raises ``RuntimeError`` if LibreOffice is not found or conversion
    fails; raises ``FileNotFoundError`` if *pptx_path* does not exist.

    The conversion runs in a temporary directory that is cleaned up on exit.
    """
    if not pptx_path.is_file():
        raise FileNotFoundError(f"pptx_to_pngs_b64: not found: {pptx_path}")

    lo = shutil.which("libreoffice") or shutil.which("soffice")
    if not lo:
        raise RuntimeError(
            "pptx_to_pngs_b64: libreoffice / soffice not found on PATH. "
            "Install LibreOffice to enable overlay mode."
        )

    with tempfile.TemporaryDirectory(prefix="feinschliff_wf_") as tmp_str:
        tmp = Path(tmp_str)
        # Copy input to temp dir so LibreOffice writes outputs alongside it.
        src = tmp / pptx_path.name
        shutil.copy2(pptx_path, src)

        cmd = [lo, "--headless", "--convert-to", "png", "--outdir", str(tmp), str(src)]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                f"pptx_to_pngs_b64: LibreOffice timed out after {timeout}s. "
                "Increase the timeout parameter or check for a hung soffice process."
            ) from exc
        if result.returncode != 0:
            raise RuntimeError(
                f"pptx_to_pngs_b64: LibreOffice exited {result.returncode}:\n"
                f"{result.stderr.strip()}"
            )

        # LibreOffice names output files as:
        #   <stem>.png          — when a single-slide file produces one PNG
        #   <stem>1.png, <stem>2.png, ... — multiple slides (1-based index)
        # The multi-slide naming is used even for single slides in some LO versions.
        stem = src.stem
        png_files = _collect_output_pngs(tmp, stem)
        if not png_files:
            raise RuntimeError(
                f"pptx_to_pngs_b64: LibreOffice ran but produced no PNG files in {tmp}. "
                f"stdout: {result.stdout.strip()}"
            )

        return [
            base64.b64encode(p.read_bytes()).decode("ascii")
            for p in png_files
        ]


def slide_to_b64(
    pptx_path: Path,
    *,
    slide_index: int = 0,
    timeout: int = 60,
) -> str:
    """Return a single slide as a base64-encoded PNG string.

    *slide_index* is 0-based. Raises ``IndexError`` if the index is out of
    range for the number of slides produced by LibreOffice.
    """
    b64_list = pptx_to_pngs_b64(pptx_path, timeout=timeout)
    if slide_index >= len(b64_list):
        raise IndexError(
            f"slide_to_b64: slide_index={slide_index} but PPTX produced "
            f"{len(b64_list)} slide(s)"
        )
    return b64_list[slide_index]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _collect_output_pngs(outdir: Path, stem: str) -> list[Path]:
    """Return PNG files produced by LibreOffice for a given input stem.

    The numbered scheme (``<stem>1.png``, ``<stem>2.png``, …) is checked
    first; if at least one numbered file exists, single-file naming is not
    consulted. When no numbered file exists, the single-file fallback
    (``<stem>.png``) is returned. No glob fallback is used: a lexicographic
    scan would misorder slides ≥10 (``slide10.png`` < ``slide2.png``) and a
    missing expected output is better surfaced upstream as an empty list
    than silently misordered.
    """
    numbered: list[Path] = []
    idx = 1
    while True:
        candidate = outdir / f"{stem}{idx}.png"
        if not candidate.is_file():
            break
        numbered.append(candidate)
        idx += 1

    if numbered:
        return numbered

    single = outdir / f"{stem}.png"
    if single.is_file():
        return [single]

    return []
