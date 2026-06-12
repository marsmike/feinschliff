"""Text fitting helpers: height estimation, autoshrink, soft-hyphenation.

Brand-pack helpers reach for these to make text behave inside fixed bounding
boxes without hand-tuning every slide. Avoids two recurring failure modes:

1. Title at fixed size wraps to two lines and overflows into the cards below
   (because the reserved height assumed one line).
2. German compounds like "Unterrichtsplanung" break mid-word because
   python-pptx wraps purely on whitespace.

Width prediction prefers REAL font metrics (fontconfig + PIL, via
`feinschmiede.text.measure`) whenever the requested family resolves to an
actual font file on the build host; the per-font character-width ratios
below are the fallback when it doesn't. Runtime-registered brand metrics
(`register_font_metrics`) always win over measurement — they encode
operator intent for fonts the build host can't resolve. Set
`FEINSCHMIEDE_NO_REAL_METRICS=1` to force the heuristic path
(deterministic CI / A-B debugging). The verify pass stays authoritative.
"""
from __future__ import annotations

import math

import pyphen

from feinschmiede.geometry import units
from feinschmiede.text import measure as _measure


_EMU_PER_PT = units.EMU_PER_PT

# Empirical average glyph widths as fraction of font size. Tune per brand by
# rendering a swatch and measuring. The "default" entry is the fallback for
# unknown fonts. Used only when real measurement is unavailable — except for
# families in _REGISTERED, whose ratios always win.
_FONT_WIDTH_RATIO: dict[str, dict[str, float]] = {
    "Open Sans":         {"normal": 0.50, "bold": 0.54},
    "Noto Sans":         {"normal": 0.51, "bold": 0.55},
    "Consolas":          {"normal": 0.55, "bold": 0.55},
    "Noto Sans Mono":    {"normal": 0.60, "bold": 0.60},
    "JetBrains Mono":    {"normal": 0.60, "bold": 0.60},
    "default":           {"normal": 0.52, "bold": 0.56},
}

# Families registered at runtime via register_font_metrics(). Their table
# ratios beat real measurement: registration is operator intent (typically
# for proprietary fonts the build host can't resolve), while the builtin
# table entries are just defaults that measurement should beat.
_REGISTERED: set[str] = set()


def register_font_metrics(family: str, *, normal: float, bold: float) -> None:
    """Register / override the average-glyph-width ratios for *family*.

    Brand packs ship metrics for their own (often proprietary) fonts via a
    `font-metrics` block in tokens.json — the build pipeline registers them
    here, so the slot-budget / verify-static width predictors stay accurate
    without this module hardcoding any client font name. Registered ratios
    take precedence over real measurement for that family.
    """
    _FONT_WIDTH_RATIO[family] = {"normal": float(normal), "bold": float(bold)}
    _REGISTERED.add(family)


def has_real_metrics(font: str, bold: bool = False) -> bool:
    """True when textfit's predictions for *font* come from real measured
    glyph widths (font resolved AND not overridden by registered ratios)."""
    return font not in _REGISTERED and _measure.find_font_file(font, bold=bold) is not None


def _avg_char_width_emu(font: str, size_pt: float, bold: bool) -> float:
    # Priority: runtime-registered brand metrics (operator intent for fonts
    # we can't resolve) > measured real metrics > builtin ratio table.
    if font not in _REGISTERED:
        measured = _measure.avg_char_width_ratio(font, bold=bold)
        if measured is not None:
            return measured * size_pt * _EMU_PER_PT
    table = _FONT_WIDTH_RATIO.get(font, _FONT_WIDTH_RATIO["default"])
    ratio = table["bold"] if bold else table["normal"]
    return ratio * size_pt * _EMU_PER_PT


def _greedy_wrap_real(line: str, font: str, size_pt: float, bold: bool,
                      width_emu: int) -> list[list[str]] | None:
    """Greedy word-wrap with measured widths. None when no real metrics.
    Splits on regular spaces only — NBSP-glued tokens stay together, like
    the heuristic packer.

    Families in _REGISTERED return None too: their registered ratios always
    win, so callers fall back to heuristic packing with those ratios instead
    of a measured wrap that would contradict them.
    """
    if font in _REGISTERED:
        return None
    width_pt = width_emu / _EMU_PER_PT
    lines: list[list[str]] = [[]]
    cur = ""
    for word in line.split(" "):
        cand = word if not cur else f"{cur} {word}"
        w = _measure.line_width_pt(cand, font, size_pt, bold=bold)
        if w is None:
            return None
        if w <= width_pt or not lines[-1]:
            lines[-1].append(word)
            cur = cand
        else:
            lines.append([word])
            cur = word
    return lines


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

    Counts explicit '\\n' newlines plus soft-wrap lines — measured greedy
    word-wrap when real font metrics resolve, character count vs. column
    width otherwise. Soft hyphens (U+00AD) are ignored in the count since
    they are invisible unless a wrap actually breaks at one.

    Height is `(n-1) * line_height + 1em`: inter-line leading applies only
    BETWEEN lines, and the trailing line contributes its em box, not a full
    leading slot. PowerPoint never clips a text box without explicit
    autofit — the last line's ascent/descent overshoot beyond the em box
    bleeds outside the shape invisibly. Counting `n * line_height` instead
    made every decompiled single-line title in a snug source-sized box
    "overflow" by the phantom trailing leading, which autoshrink then
    "fixed" by shrinking text the source renders at full size.
    """
    if not text:
        return 0
    line_h = _line_height_emu(size_pt, line_height)
    width_pt = width_emu / _EMU_PER_PT
    cols: int | None = None    # heuristic columns, computed lazily on fallback
    total_lines = 0
    for hard_line in text.split("\n"):
        visible = hard_line.replace("­", "")
        if not visible:
            total_lines += 1
            continue
        wrapped = _greedy_wrap_real(visible, font, size_pt, bold, width_emu)
        if wrapped is not None:
            for line_words in wrapped:
                if len(line_words) == 1:
                    w_pt = _measure.line_width_pt(line_words[0], font, size_pt, bold=bold)
                    if w_pt is not None and w_pt > width_pt:
                        # Renderers break over-wide words mid-word (and at soft
                        # hyphens, stripped above); count the minimum lines the
                        # glyph mass needs. Over-estimates vs. syllable
                        # breaking — the safe direction for overflow checks.
                        total_lines += max(1, math.ceil(w_pt / width_pt))
                        continue
                total_lines += 1
        else:
            if cols is None:
                cols = chars_per_line(font, size_pt, bold, width_emu)
            # ceil(len / cols)
            total_lines += max(1, (len(visible) + cols - 1) // cols)
    if total_lines == 0:
        return 0
    em_h = int(size_pt * _EMU_PER_PT)
    return (total_lines - 1) * line_h + min(line_h, em_h)


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

    The wrap uses measured widths when real font metrics resolve (and the
    family has no registered ratios), character-count packing otherwise.

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

    # Measured greedy wrap when available; heuristic char packing otherwise.
    # Strip soft hyphens (U+00AD) before measuring, mirroring
    # measure_height_emu — they're invisible unless a break lands on one, and
    # correctness shouldn't depend on per-font SHY advance. The NBSP glue
    # below still happens on the ORIGINAL text.
    visible = text.replace("­", "")
    lines = _greedy_wrap_real(visible, font, size_pt, bold, width_emu)
    if lines is None:
        avg_w = _avg_char_width_emu(font, size_pt, bold)
        chars_per_line = max(1, int(width_emu / avg_w))

        # Greedy line packing: count NBSPs as part of the token (no break).
        lines = [[]]
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
