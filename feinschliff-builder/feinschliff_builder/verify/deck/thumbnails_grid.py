"""Compose per-slide PNG thumbnails into a single multi-page PDF in a 4-column grid.

Used by /deck critique to produce a 'print-and-lay-on-table' view of
the deck — humans + LLMs both review structure better seeing 4-8 slides
at once than scrolling through one-up renders.

Implementation: PIL-only (no reportlab dep). PIL natively writes
multi-page PDFs via `Image.save(..., format='PDF', save_all=True,
append_images=[...])`, where each page is a separate `Image` object.
We render each page into a white RGB canvas sized to `page_size_in` at
a fixed 100 DPI, paste thumbnails into the 4 × `rows_per_page` grid
preserving aspect ratio, then stack the page images into the PDF.
"""
from __future__ import annotations

import math
from pathlib import Path


_DPI = 100  # canvas resolution; PIL PDF inherits page size from canvas px @ 72dpi


def render_thumbnails_grid_pdf(
    png_paths: list[Path],
    output_pdf: Path,
    *,
    columns: int = 4,
    page_size_in: tuple[float, float] = (11.0, 8.5),  # US Letter landscape
    margin_in: float = 0.25,
    gap_in: float = 0.15,
) -> Path:
    """Compose `png_paths` into a 4-column grid PDF at `output_pdf`.

    Layout: `columns` columns × up to `columns` rows per page (so 4 × 4 = 16
    thumbs per page by default). Each cell is sized to fit the page minus
    margins and gaps; each thumb is centered in its cell, aspect ratio
    preserved.

    Parent directories of `output_pdf` are created if missing.
    """
    from PIL import Image

    if not png_paths:
        raise ValueError("render_thumbnails_grid_pdf: png_paths is empty")

    rows_per_page = columns  # square page-grid: 4 × 4 = 16 cells / page
    cells_per_page = columns * rows_per_page

    page_w_px = int(round(page_size_in[0] * _DPI))
    page_h_px = int(round(page_size_in[1] * _DPI))
    margin_px = int(round(margin_in * _DPI))
    gap_px = int(round(gap_in * _DPI))

    inner_w = page_w_px - 2 * margin_px - (columns - 1) * gap_px
    inner_h = page_h_px - 2 * margin_px - (rows_per_page - 1) * gap_px
    cell_w = inner_w // columns
    cell_h = inner_h // rows_per_page

    # Load all thumbs eagerly — they're already on disk from the verify
    # step, and modest in count. Convert to RGB so the PDF write doesn't
    # trip on RGBA / palette modes.
    thumbs: list[Image.Image] = []
    for p in png_paths:
        with Image.open(p) as im:
            thumbs.append(im.convert("RGB").copy())

    n_pages = math.ceil(len(thumbs) / cells_per_page)
    pages: list[Image.Image] = []
    for page_idx in range(n_pages):
        canvas = Image.new("RGB", (page_w_px, page_h_px), color=(255, 255, 255))
        start = page_idx * cells_per_page
        end = min(start + cells_per_page, len(thumbs))
        for cell_idx, thumb in enumerate(thumbs[start:end]):
            row = cell_idx // columns
            col = cell_idx % columns
            cell_x = margin_px + col * (cell_w + gap_px)
            cell_y = margin_px + row * (cell_h + gap_px)
            # Fit thumb into (cell_w, cell_h) preserving aspect.
            tw, th = thumb.size
            scale = min(cell_w / tw, cell_h / th)
            new_w = max(1, int(round(tw * scale)))
            new_h = max(1, int(round(th * scale)))
            fitted = thumb.resize((new_w, new_h), Image.LANCZOS)
            # Center in cell.
            paste_x = cell_x + (cell_w - new_w) // 2
            paste_y = cell_y + (cell_h - new_h) // 2
            canvas.paste(fitted, (paste_x, paste_y))
        pages.append(canvas)

    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    first, rest = pages[0], pages[1:]
    first.save(
        str(output_pdf),
        format="PDF",
        save_all=True,
        append_images=rest,
        resolution=float(_DPI),
    )
    return output_pdf
