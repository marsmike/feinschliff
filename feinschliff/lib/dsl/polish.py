"""Pure text-normalization for the v2 DSL emitter.

Applied to every text run before it reaches python-pptx. Independent of
python-pptx — testable in isolation. The emitter calls `normalize_text`
once per run.

Locale-aware quote conventions (`en` → curly double, `de` → German low-9
+ left-double). Unknown locales fall back to `en`. All normalizations
are idempotent — calling twice yields the same result.
"""
from __future__ import annotations

import re


# Locale-specific quote pairs (open, close) for double quotes.
_QUOTE_DOUBLE: dict[str, tuple[str, str]] = {
    "en": ("“", "”"),    # “ ”
    "de": ("„", "“"),    # „ “
    "fr": ("« ", " »"),  # « ... »
}


# Hyphen-minus → true minus only when followed by a digit AND not preceded by
# a word character (so "data-driven" stays hyphenated, "-1.2%" gets U+2212).
_TRUE_MINUS_RE = re.compile(r"(?<![\w-])-(?=\d)")

# Double-hyphen → em-dash.
_EM_DASH_RE = re.compile(r"--")

# Triple-dot → horizontal ellipsis.
_ELLIPSIS_RE = re.compile(r"\.{3}")

# Multi-space → single space.
_DOUBLE_SPACE_RE = re.compile(r"  +")


def _smart_quotes(text: str, locale: str) -> str:
    """Replace straight double quotes with locale-appropriate curly quotes.

    Simple alternation: first `"` is open, second is close, third is
    open, etc. Idempotent: already-curly quotes pass through unchanged.
    """
    open_q, close_q = _QUOTE_DOUBLE.get(locale, _QUOTE_DOUBLE["en"])
    out_chars: list[str] = []
    is_open = True
    for ch in text:
        if ch == '"':
            out_chars.append(open_q if is_open else close_q)
            is_open = not is_open
        else:
            out_chars.append(ch)
    return "".join(out_chars)


def normalize_text(text: str, *, locale: str = "en") -> str:
    """Apply the full normalization stack to `text`. Idempotent."""
    if not text:
        return text
    text = _smart_quotes(text, locale)
    text = _EM_DASH_RE.sub("—", text)
    text = _TRUE_MINUS_RE.sub("−", text)
    text = _ELLIPSIS_RE.sub("…", text)
    text = _DOUBLE_SPACE_RE.sub(" ", text)
    return text
