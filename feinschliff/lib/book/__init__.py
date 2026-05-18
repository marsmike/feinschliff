"""Speaker-book PDF — annotated presenter handbook generator.

Different deliverable from the projected deck: where the PPTX is what
the audience sees on screen, the book PDF is what the presenter reads
ahead of time. It bundles each slide's thumbnail alongside its claim,
audience_fit, role tag, and speaker notes, framed by deck-level
front matter (takeaway, audience, frame, red_line, hook).

See `references/speaker-notes.md` for the design rules the book
surfaces.
"""

from .book_pdf import (
    BookSlide,
    DeckFrontMatter,
    compose_book_pdf,
    render_front_matter_page,
    render_slide_page,
)

__all__ = [
    "BookSlide",
    "DeckFrontMatter",
    "compose_book_pdf",
    "render_front_matter_page",
    "render_slide_page",
]
