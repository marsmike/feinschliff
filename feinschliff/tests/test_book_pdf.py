"""Speaker-book PDF — page renderer + composer tests.

Covers the deterministic rendering surface (front matter, per-slide
pages, multi-page assembly). Visual fidelity / brand styling is
out-of-scope for unit tests — those iterate in code review."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from lib.book import (
    BookSlide,
    DeckFrontMatter,
    compose_book_pdf,
    render_front_matter_page,
    render_slide_page,
)
from lib.book.book_pdf import PAGE_H_PX, PAGE_W_PX


def _front_matter() -> DeckFrontMatter:
    return DeckFrontMatter(
        takeaway="Polish time collapsed from 3 hrs to 15 min per deck",
        audience="exec",
        audience_notes="Time-poor, outcomes-driven; stops listening at 30s buildup.",
        frame="sparkline",
        frame_rationale="Vision pitch oscillating pain and future; PSSR rejected.",
        red_line="Pain → Solution demo → Results → What this unlocks.",
        hook_technique="contrast",
        hook_opener="Five years ago this took a week. Today it takes 15 minutes.",
    )


def _book_slides(thumbnail: Path | None = None) -> list[BookSlide]:
    return [
        BookSlide(
            index=0, role="hook",
            claim="Polish time has collapsed.",
            notes=("Storyline: pain → demo → results.\n"
                   "• Open with the time-collapse stat.\n"
                   "• Hand off to the live demo at 0:45."),
            audience_fit="Execs care about the outcome, not the loop.",
            thumbnail_path=thumbnail,
        ),
        BookSlide(
            index=1, role="context",
            claim="Five years ago, polish took a week.",
            notes="• Writer/designer/reviewer cycles.\n• Cost ~$8k per deck.",
            audience_fit="Anchor cost so the next slide's contrast lands.",
            thumbnail_path=thumbnail,
        ),
    ]


def test_front_matter_page_dimensions():
    page = render_front_matter_page(_front_matter())
    assert page.size == (PAGE_W_PX, PAGE_H_PX)
    assert page.mode == "RGB"


def test_front_matter_renders_without_hook():
    """Hook fields are optional; the renderer skips them cleanly."""
    fm = DeckFrontMatter(
        takeaway="A short takeaway.",
        audience="exec",
        audience_notes="Time-poor.",
        frame="scqa",
        frame_rationale="Standard reach-for-it.",
        red_line="Arc.",
    )
    page = render_front_matter_page(fm)
    assert page.size == (PAGE_W_PX, PAGE_H_PX)


def test_slide_page_dimensions():
    slides = _book_slides()
    page = render_slide_page(slides[0])
    assert page.size == (PAGE_W_PX, PAGE_H_PX)


def test_slide_page_with_real_thumbnail(tmp_path: Path):
    """A real PNG thumbnail is composited onto the page."""
    thumb_path = tmp_path / "thumb.png"
    Image.new("RGB", (1600, 900), (200, 220, 240)).save(thumb_path)
    page = render_slide_page(_book_slides(thumbnail=thumb_path)[0])
    # Crude check that the thumbnail composited somewhere on the page:
    # the top stripe (where the thumbnail goes) should contain a non-paper
    # pixel near the centre.
    centre = page.getpixel((PAGE_W_PX // 2, 220))
    assert centre != (255, 255, 255)


def test_slide_page_handles_missing_thumbnail(tmp_path: Path):
    """A non-existent thumbnail path is skipped — page still renders."""
    bs = BookSlide(
        index=0, role="hook",
        claim="No thumb yet.",
        notes="notes",
        audience_fit="fit",
        thumbnail_path=tmp_path / "does-not-exist.png",
    )
    page = render_slide_page(bs)
    assert page.size == (PAGE_W_PX, PAGE_H_PX)


def _pdf_page_count(pdf_path: Path) -> int:
    """Count `/Type /Page ` (with trailing space — distinguishes from
    `/Type /Pages` for the root pages tree). Coarse but accurate for
    the PDFs PIL writes."""
    data = pdf_path.read_bytes()
    return data.count(b"/Type /Page ") + data.count(b"/Type /Page\n")


def test_compose_book_pdf_writes_multipage(tmp_path: Path):
    """End-to-end: compose front matter + N slides into a PDF and
    confirm the file has the expected page count."""
    out = tmp_path / "speaker-book.pdf"
    compose_book_pdf(_front_matter(), _book_slides(), out)
    assert out.is_file()
    assert out.stat().st_size > 0
    assert out.read_bytes().startswith(b"%PDF-"), "not a valid PDF header"
    # 1 front matter + 2 slides = 3 pages.
    assert _pdf_page_count(out) == 3


def test_compose_book_pdf_with_empty_slides_still_renders_front_matter(
    tmp_path: Path,
):
    out = tmp_path / "front-only.pdf"
    compose_book_pdf(_front_matter(), [], out)
    assert out.is_file()
    assert out.read_bytes().startswith(b"%PDF-")
    assert _pdf_page_count(out) == 1
