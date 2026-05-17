"""Text fitting helpers: height estimation, autoshrink, soft-hyphenation.

Brand-pack helpers reach for these to make text behave inside fixed bounding
boxes without hand-tuning every slide. Avoids two recurring failure modes:

1. Title at fixed size wraps to two lines and overflows into the cards below
   (because the reserved height assumed one line).
2. German compounds like "Unterrichtsplanung" break mid-word because
   python-pptx wraps purely on whitespace.

Height estimation here is intentionally rough — python-pptx does not lay out
text. The per-font character-width ratios are empirical and good enough to
pick a font size that *will* fit; the verify pass is still authoritative.
"""
from __future__ import annotations


import pyphen


_EMU_PER_PT = 12700

# Empirical average glyph widths as fraction of font size. Tune per brand by
# rendering a swatch and measuring. The "default" entry is the fallback for
# unknown fonts.
_FONT_WIDTH_RATIO: dict[str, dict[str, float]] = {
    "Open Sans": {"normal": 0.50, "bold": 0.54},
    "Consolas":  {"normal": 0.55, "bold": 0.55},
    "default":   {"normal": 0.52, "bold": 0.56},
}


def _avg_char_width_emu(font: str, size_pt: float, bold: bool) -> float:
    table = _FONT_WIDTH_RATIO.get(font, _FONT_WIDTH_RATIO["default"])
    ratio = table["bold"] if bold else table["normal"]
    return ratio * size_pt * _EMU_PER_PT


def supported_fonts() -> frozenset[str]:
    """Font names for which explicit width ratios are registered (excludes 'default')."""
    return frozenset(k for k in _FONT_WIDTH_RATIO if k != "default")


def chars_per_line(font: str, size_pt: float, bold: bool, width_emu: int) -> int:
    """Estimate how many average characters fit on one line at *width_emu* EMU."""
    avg_w = _avg_char_width_emu(font, size_pt, bold)
    return max(1, int(width_emu / avg_w))


def _line_height_emu(size_pt: float, line_height: float) -> int:
    return int(size_pt * line_height * _EMU_PER_PT)


def measure_height_emu(
    text: str,
    *,
    font: str = "Open Sans",
    size_pt: float = 18,
    bold: bool = False,
    width_emu: int,
    line_height: float = 1.2,
) -> int:
    """Estimate rendered height (EMU) of `text` at `font`/`size_pt` in `width_emu`.

    Counts explicit '\\n' newlines plus soft-wrap lines estimated from character
    count vs. column width. Soft hyphens (U+00AD) are ignored in the count
    since they are invisible unless a wrap actually breaks at one.
    """
    if not text:
        return 0
    avg_w = _avg_char_width_emu(font, size_pt, bold)
    chars_per_line = max(1, int(width_emu / avg_w))
    line_h = _line_height_emu(size_pt, line_height)
    total_lines = 0
    for hard_line in text.split("\n"):
        visible = hard_line.replace("­", "")
        if not visible:
            total_lines += 1
            continue
        # ceil(len / chars_per_line)
        total_lines += max(1, (len(visible) + chars_per_line - 1) // chars_per_line)
    return total_lines * line_h


def fits(
    text: str,
    *,
    font: str = "Open Sans",
    size_pt: float = 18,
    bold: bool = False,
    width_emu: int,
    height_emu: int,
    line_height: float = 1.2,
) -> bool:
    return measure_height_emu(
        text, font=font, size_pt=size_pt, bold=bold,
        width_emu=width_emu, line_height=line_height,
    ) <= height_emu


def autoshrink_size(
    text: str,
    *,
    font: str = "Open Sans",
    max_size_pt: float,
    min_size_pt: float = 10,
    bold: bool = False,
    width_emu: int,
    height_emu: int,
    step: float = 2,
    line_height: float = 1.2,
) -> float:
    """Largest size in [min, max] (descending by `step`) that fits `text` into
    `width_emu × height_emu`. Returns `min_size_pt` if no candidate fits — the
    caller decides whether to error or accept the squeeze.
    """
    size = max_size_pt
    while size >= min_size_pt:
        if fits(text, font=font, size_pt=size, bold=bold,
                width_emu=width_emu, height_emu=height_emu,
                line_height=line_height):
            return size
        size -= step
    return min_size_pt


# Soft-hyphen insertion via pyphen. Dict objects are cached per-process.
_HYPHEN_DICTS: dict[str, pyphen.Pyphen] = {}


def _get_dict(lang: str) -> pyphen.Pyphen:
    if lang not in _HYPHEN_DICTS:
        _HYPHEN_DICTS[lang] = pyphen.Pyphen(lang=lang)
    return _HYPHEN_DICTS[lang]


_NBSP = " "


def prevent_orphan(
    text: str,
    *,
    font: str,
    size_pt: float,
    bold: bool,
    width_emu: int,
) -> str:
    """If a greedy wrap of `text` at the given width would put a single
    word on the final line, replace the space between the last two words
    with U+00A0 (NBSP) so the pair wraps together. Otherwise return `text`
    unchanged.

    Idempotent: if the text already contains an NBSP between the last two
    words (no regular space there), the orphan check sees the pair as one
    token and leaves it alone.
    """
    # Tokenize on regular spaces only — NBSP is treated as glue.
    parts = text.split(" ")
    if len(parts) < 3:
        return text   # too short to orphan
    # Already-glued by a prior call: the last regular-space-separated token
    # contains an NBSP. Bail rather than double-glue further left.
    if " " in parts[-1]:
        return text

    avg_w = _avg_char_width_emu(font, size_pt, bold)
    chars_per_line = max(1, int(width_emu / avg_w))

    # Greedy line packing: count NBSPs as part of the token (no break).
    lines: list[list[str]] = [[]]
    current_len = 0
    for word in parts:
        # Visible length sees NBSP as one cell, just like a letter.
        word_len = len(word)
        sep = 1 if lines[-1] else 0
        prospective = current_len + sep + word_len
        if prospective <= chars_per_line or not lines[-1]:
            lines[-1].append(word)
            current_len = prospective
        else:
            lines.append([word])
            current_len = word_len

    # Orphan condition: more than one line AND last line has exactly one word.
    if len(lines) > 1 and len(lines[-1]) == 1:
        # Glue the last word to the previous via NBSP (replace exactly the
        # final regular space). rsplit on a single space gives ('head','tail').
        head, sep, tail = text.rpartition(" ")
        if sep == " ":
            return head + _NBSP + tail
    return text


def hyphenate(
    text: str,
    *,
    lang: str = "de_DE",
    soft_hyphen: str = "­",
    min_word_len: int = 8,
) -> str:
    """Insert U+00AD soft hyphens so python-pptx breaks long compounds at
    syllable boundaries instead of mid-word.

    Words shorter than `min_word_len` are left alone (no point hyphenating
    "der"). The soft hyphen is invisible unless a wrap actually occurs at it.
    """
    out_tokens = []
    for token in text.split(" "):
        if len(token) >= min_word_len and any(c.isalpha() for c in token):
            try:
                out_tokens.append(_get_dict(lang).inserted(token, hyphen=soft_hyphen))
            except Exception:
                # Unknown language or pyphen failure — leave the word as-is.
                out_tokens.append(token)
        else:
            out_tokens.append(token)
    return " ".join(out_tokens)
