"""Annotated speaker-book PDF — page renderer + composer.

Pipeline:

  brief.json + plan.yaml + per-slide PNG thumbnails
                  │
                  ▼
  DeckFrontMatter + list[BookSlide]
                  │
                  ▼
  PIL.Image per page (front matter + N slide pages)
                  │
                  ▼
  multi-page PDF (via PIL's save_all=True)

This module owns the data shapes and the page renderers. The caller
(`cli/deck.py:cmd_book`) orchestrates input loading + thumbnail
rendering.

Design choices:

- Pages are rendered directly with PIL primitives, not SVG → cairosvg.
  Simpler, no font-discovery dance for cairosvg, and the visual
  vocabulary is intentionally minimal (book is a reading deliverable,
  not a presentation).
- Multi-page PDF assembled via `Image.save(..., save_all=True,
  append_images=[…])`. Zero new dependencies — PIL is already in the
  project's runtime deps.
- Letter-size page (8.5×11in at 144 DPI = 1224×1584 px). Vertical
  orientation matches reading-deliverable convention.
- Brand styling is intentionally deferred: this initial implementation
  uses system fonts and ink/paper colors only. A follow-up wires the
  brand's Tokens (display family, accent color, etc.) into the page
  renderer so the book picks up brand identity end-to-end.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


# ── page geometry ──────────────────────────────────────────────────────

PAGE_W_PX = 1224          # 8.5in × 144 DPI
PAGE_H_PX = 1584          # 11in × 144 DPI
MARGIN_PX = 96            # ~2/3in margin

_INK_RGB = (16, 24, 35)
_GRAPHITE_RGB = (74, 88, 111)
_FOG_RGB = (170, 178, 190)
_PAPER_RGB = (255, 255, 255)
_ACCENT_RGB = (220, 86, 40)   # placeholder until brand tokens are wired


# ── data shapes ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DeckFrontMatter:
    """Deck-level data surfaced on the book's front matter page. Maps
    directly onto fields in `design_brief.schema.json`."""
    takeaway: str
    audience: str
    audience_notes: str
    frame: str
    frame_rationale: str
    red_line: str
    hook_technique: str = ""
    hook_opener: str = ""
    deck_title: str | None = None


@dataclass(frozen=True)
class BookSlide:
    """Per-slide data surfaced on each per-slide book page."""
    index: int                       # 0-based, matches design brief
    role: str                        # hook / context / complication / …
    claim: str                       # the slide's title-in-draft
    notes: str                       # speaker notes, possibly multi-line
    audience_fit: str                # "why this works for this audience"
    thumbnail_path: Path | None      # PNG of the rendered slide
    section_label: str | None = None # optional super-header (act / phase)


# ── helpers ────────────────────────────────────────────────────────────


def _load_font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    """Resolve a system font face — best-effort, falls back to PIL default.

    The book uses system fonts to avoid an asset-pack dependency on the
    brand's display face. A follow-up wires the brand's Tokens through
    so the book picks up the same family as the deck.
    """
    candidates_regular = [
        "DejaVuSans.ttf", "Arial.ttf", "Helvetica.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    candidates_bold = [
        "DejaVuSans-Bold.ttf", "Arial-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for name in (candidates_bold if bold else candidates_regular):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap_text(
    text: str, font: ImageFont.ImageFont, max_width: int,
) -> list[str]:
    """Greedy word-wrap with explicit-newline awareness. Returns the
    sequence of physical lines to render."""
    out: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        if not words:
            out.append("")
            continue
        current = words[0]
        for w in words[1:]:
            candidate = f"{current} {w}"
            width = _text_width(candidate, font)
            if width <= max_width:
                current = candidate
            else:
                out.append(current)
                current = w
        out.append(current)
    return out


def _text_width(s: str, font: ImageFont.ImageFont) -> int:
    """Compatibility wrapper — getbbox is the modern Pillow API; default
    fonts older builds return None for it, so fall back to getsize."""
    try:
        bbox = font.getbbox(s)
        return bbox[2] - bbox[0]
    except AttributeError:
        return font.getsize(s)[0]


def _draw_wrapped(
    draw: ImageDraw.ImageDraw, x: int, y: int, text: str,
    *, font: ImageFont.ImageFont, fill, max_width: int,
    line_height: float = 1.4,
) -> int:
    """Draw word-wrapped text starting at (x, y). Returns the y
    coordinate immediately below the rendered block."""
    lines = _wrap_text(text, font, max_width)
    # getbbox returns (l, t, r, b) — we want the font's nominal line height.
    try:
        ascent, descent = font.getmetrics()
        line_px = int((ascent + descent) * line_height)
    except AttributeError:
        line_px = int(font.size * line_height)
    cur_y = y
    for line in lines:
        draw.text((x, cur_y), line, font=font, fill=fill)
        cur_y += line_px
    return cur_y


# ── page renderers ─────────────────────────────────────────────────────


def render_front_matter_page(fm: DeckFrontMatter) -> Image.Image:
    """Render the book's opening page — a key/value list of deck-level
    brief fields plus the deck title (if supplied)."""
    page = Image.new("RGB", (PAGE_W_PX, PAGE_H_PX), _PAPER_RGB)
    draw = ImageDraw.Draw(page)

    eyebrow_font = _load_font(20)
    h1_font = _load_font(56, bold=True)
    h2_font = _load_font(28, bold=True)
    body_font = _load_font(22)
    content_w = PAGE_W_PX - 2 * MARGIN_PX

    y = MARGIN_PX
    draw.text((MARGIN_PX, y), "SPEAKER BOOK",
              font=eyebrow_font, fill=_ACCENT_RGB)
    y += 36

    title = fm.deck_title or "Deck companion"
    y = _draw_wrapped(
        draw, MARGIN_PX, y, title, font=h1_font, fill=_INK_RGB,
        max_width=content_w, line_height=1.15,
    )
    y += 24

    # Horizontal rule, accent.
    draw.line(
        [(MARGIN_PX, y), (MARGIN_PX + content_w, y)],
        fill=_ACCENT_RGB, width=3,
    )
    y += 32

    sections: list[tuple[str, str]] = [
        ("Takeaway", fm.takeaway),
        ("Audience", f"{fm.audience} — {fm.audience_notes}"),
        ("Frame", f"{fm.frame} — {fm.frame_rationale}"),
        ("Red line", fm.red_line),
    ]
    if fm.hook_opener:
        sections.append(("Hook",
                         f"{fm.hook_technique}: “{fm.hook_opener}”"))

    for heading, body in sections:
        if not body:
            continue
        draw.text((MARGIN_PX, y), heading,
                  font=h2_font, fill=_INK_RGB)
        y += 40
        y = _draw_wrapped(
            draw, MARGIN_PX, y, body, font=body_font, fill=_GRAPHITE_RGB,
            max_width=content_w, line_height=1.4,
        )
        y += 28

    return page


def render_slide_page(slide: BookSlide) -> Image.Image:
    """Render one per-slide page. Layout (top to bottom):

      eyebrow  : "Slide N — <role>"  +  optional section_label
      thumbnail: rendered PNG, fit to content width (preserves aspect)
      claim    : the slide's title
      notes    : speaker notes block
      audience_fit: italicised "why this works for this audience"
    """
    page = Image.new("RGB", (PAGE_W_PX, PAGE_H_PX), _PAPER_RGB)
    draw = ImageDraw.Draw(page)

    eyebrow_font = _load_font(18)
    claim_font = _load_font(38, bold=True)
    body_font = _load_font(20)
    notes_heading_font = _load_font(20, bold=True)
    content_w = PAGE_W_PX - 2 * MARGIN_PX

    y = MARGIN_PX
    eyebrow = f"SLIDE {slide.index + 1} — {slide.role.upper()}"
    if slide.section_label:
        eyebrow = f"{slide.section_label.upper()}   ·   {eyebrow}"
    draw.text((MARGIN_PX, y), eyebrow,
              font=eyebrow_font, fill=_ACCENT_RGB)
    y += 32

    # Thumbnail — letterboxed to content width, max 9:16 ratio cap so a
    # square crop doesn't blow out the page.
    if slide.thumbnail_path and slide.thumbnail_path.is_file():
        try:
            with Image.open(slide.thumbnail_path) as thumb:
                thumb.load()
                tw, th = thumb.size
                scale = content_w / tw
                new_w = content_w
                new_h = int(th * scale)
                max_h = int(PAGE_H_PX * 0.42)
                if new_h > max_h:
                    scale = max_h / th
                    new_h = max_h
                    new_w = int(tw * scale)
                resized = thumb.resize((new_w, new_h), Image.LANCZOS)
                x = MARGIN_PX + (content_w - new_w) // 2
                page.paste(resized, (x, y))
                # 1px hairline frame.
                draw.rectangle(
                    [(x, y), (x + new_w - 1, y + new_h - 1)],
                    outline=_FOG_RGB, width=1,
                )
                y += new_h + 28
        except OSError:
            pass

    y = _draw_wrapped(
        draw, MARGIN_PX, y, slide.claim, font=claim_font, fill=_INK_RGB,
        max_width=content_w, line_height=1.15,
    )
    y += 16

    if slide.notes:
        draw.text((MARGIN_PX, y), "What to say",
                  font=notes_heading_font, fill=_INK_RGB)
        y += 32
        y = _draw_wrapped(
            draw, MARGIN_PX, y, slide.notes,
            font=body_font, fill=_GRAPHITE_RGB,
            max_width=content_w, line_height=1.45,
        )
        y += 20

    if slide.audience_fit:
        draw.text((MARGIN_PX, y), "Why this works for this audience",
                  font=notes_heading_font, fill=_INK_RGB)
        y += 32
        y = _draw_wrapped(
            draw, MARGIN_PX, y, slide.audience_fit,
            font=body_font, fill=_GRAPHITE_RGB,
            max_width=content_w, line_height=1.45,
        )

    return page


# ── multi-page composer ────────────────────────────────────────────────


def compose_book_pdf(
    front_matter: DeckFrontMatter,
    slides: Iterable[BookSlide],
    out_path: Path,
) -> Path:
    """Assemble the speaker-book PDF — one front-matter page followed
    by one page per slide. Returns the output path.

    PIL writes the multi-page PDF natively via `save_all=True`, so no
    extra dependency is needed beyond what's already in the project.
    """
    pages: list[Image.Image] = [render_front_matter_page(front_matter)]
    pages.extend(render_slide_page(s) for s in slides)
    if not pages:
        raise ValueError("compose_book_pdf: no pages to write")
    head, *tail = pages
    out_path.parent.mkdir(parents=True, exist_ok=True)
    head.save(
        str(out_path),
        format="PDF",
        save_all=True,
        append_images=tail,
        resolution=144.0,
    )
    return out_path
