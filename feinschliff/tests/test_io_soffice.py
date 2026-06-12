"""Command construction for the canonical soffice/pdftoppm helpers.

`pdf_to_pngs` carries a `scale_to` parameter so the brand verify loop can
route its 1920×1080 rasterisation through the canonical module (isolated
soffice `UserInstallation` profile) instead of shelling raw binaries. These
tests pin the pdftoppm argv for both modes — `-r dpi` by default,
`-scale-to-x/-scale-to-y` when `scale_to` is given — without invoking the
real binaries: `subprocess.run` is replaced by a fake that records argv and
fabricates the output files each command would have produced.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from feinschliff.io import soffice


@pytest.fixture
def capture(monkeypatch, tmp_path):
    """Monkeypatch subprocess.run inside the soffice module.

    The fake records every argv and fabricates output files: a PDF next to
    the requested `--outdir` for soffice calls, `<prefix>-1.png` for
    pdftoppm calls. Tests inspect `calls` to pin exact command construction.
    """
    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(list(cmd))
        if cmd[0] == soffice.SOFFICE:
            out_dir = Path(cmd[cmd.index("--outdir") + 1])
            src = Path(cmd[-1])
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / src.with_suffix(".pdf").name).touch()
        elif cmd[0] == soffice.PDFTOPPM:
            stem = Path(cmd[-1])
            stem.parent.mkdir(parents=True, exist_ok=True)
            Path(f"{stem}-1.png").touch()
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(soffice.subprocess, "run", fake_run)
    return calls


def test_pdf_to_pngs_default_uses_dpi(capture, tmp_path):
    pdf = tmp_path / "deck.pdf"
    pdf.touch()
    out = tmp_path / "png"
    pngs = soffice.pdf_to_pngs(pdf, out, dpi=144)
    assert capture == [
        [soffice.PDFTOPPM, "-r", "144", "-png", str(pdf), str(out / "page")]
    ]
    assert pngs == [out / "page-1.png"]


def test_pdf_to_pngs_scale_to_emits_scale_flags(capture, tmp_path):
    pdf = tmp_path / "deck.pdf"
    pdf.touch()
    out = tmp_path / "png"
    soffice.pdf_to_pngs(pdf, out, scale_to=(1920, 1080))
    (cmd,) = capture
    assert cmd == [
        soffice.PDFTOPPM, "-scale-to-x", "1920", "-scale-to-y", "1080",
        "-png", str(pdf), str(out / "page"),
    ]
    assert "-r" not in cmd


def test_pdf_to_pngs_slide_index_bounds_page_range(capture, tmp_path):
    pdf = tmp_path / "deck.pdf"
    pdf.touch()
    out = tmp_path / "png"
    soffice.pdf_to_pngs(pdf, out, slide_index=3, scale_to=(1920, 1080),
                        prefix="_p3")
    (cmd,) = capture
    assert cmd == [
        soffice.PDFTOPPM, "-scale-to-x", "1920", "-scale-to-y", "1080",
        "-png", "-f", "3", "-l", "3", str(pdf), str(out / "_p3"),
    ]


def test_pdf_to_pngs_no_output_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(
        soffice.subprocess, "run",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout=b"", stderr=b""),
    )
    pdf = tmp_path / "deck.pdf"
    pdf.touch()
    with pytest.raises(RuntimeError, match="produced no PNG"):
        soffice.pdf_to_pngs(pdf, tmp_path / "png")


def test_pptx_to_png_default_command_unchanged(capture, tmp_path):
    """Regression guard: the legacy `-r dpi` argv stays byte-identical for
    existing callers (render_brand_atlas, render_brand_preview, …)."""
    pptx = tmp_path / "deck.pptx"
    pptx.touch()
    out = tmp_path / "png"
    png = soffice.pptx_to_png(pptx, out)
    soffice_cmd, pdftoppm_cmd = capture
    assert soffice_cmd[0] == soffice.SOFFICE
    assert any(a.startswith("-env:UserInstallation=file://") for a in soffice_cmd)
    assert pdftoppm_cmd == [
        soffice.PDFTOPPM, "-r", "96", "-png",
        str(out / "deck.pdf"), str(out / "page"),
    ]
    assert png == out / "page-1.png"


def test_pptx_to_png_scale_to_passthrough(capture, tmp_path):
    pptx = tmp_path / "deck.pptx"
    pptx.touch()
    out = tmp_path / "png"
    soffice.pptx_to_png(pptx, out, scale_to=(640, 360))
    _, pdftoppm_cmd = capture
    assert pdftoppm_cmd[:6] == [
        soffice.PDFTOPPM, "-scale-to-x", "640", "-scale-to-y", "360", "-png",
    ]
