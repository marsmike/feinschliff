"""Real-font text measurement (fontconfig + PIL), shared by slide textfit,
slot budgets, and future diagram validators.

Every function degrades to None when fontconfig, PIL, or the requested font
is unavailable — callers keep their char-ratio heuristics as fallback. Set
FEINSCHMIEDE_NO_REAL_METRICS=1 to force the heuristic path (deterministic
CI / A-B debugging). PIL (pillow) is an optional dependency: feinschmiede
itself doesn't require it, the office-side consumers already do.
"""
from __future__ import annotations

import functools
import os
import shutil
import subprocess
from pathlib import Path

_MEASURE_SIZE = 100.0
_SAMPLE = ("abcdefghijklmnopqrstuvwxyz"
           "ABCDEFGHIJKLMNOPQRSTUVWXYZ 0123456789,.")


def clear_caches() -> None:
    """Reset lru caches (tests toggle env vars / font-install state)."""
    _find_font_file_cached.cache_clear()
    _font_at_measure_size.cache_clear()
    _avg_char_width_ratio_cached.cache_clear()


def _family_matches(requested: str, families: list[str]) -> bool:
    """True when fc-match resolved the REQUESTED family (not a substitute).

    `requested` may carry a weight suffix ("Open Sans SemiBold") that
    fontconfig reports as family "Open Sans" — accept when the request
    starts with the resolved family. The reverse (resolved family more
    specific than the request, e.g. "Open Sans Condensed" for "Open
    Sans") is rejected: a different-width variant would silently produce
    wrong metrics, and None correctly degrades to the heuristic path.
    """
    req = requested.strip().lower()
    fams = [f.strip().lower() for f in families if f.strip()]
    return any(req == g or req.startswith(g) for g in fams)


def find_font_file(face: str, *, bold: bool = False) -> Path | None:
    """Resolve `face` to its font file, or None when fontconfig is missing,
    the kill-switch is set, or fc-match falls back to a different family."""
    if os.environ.get("FEINSCHMIEDE_NO_REAL_METRICS") == "1":
        return None
    return _find_font_file_cached(face, bold)


@functools.lru_cache(maxsize=256)
def _find_font_file_cached(face: str, bold: bool) -> Path | None:
    fc = shutil.which("fc-match")
    if fc is None:
        return None
    pattern = f"{face}:weight=bold" if bold else face
    try:
        proc = subprocess.run(
            [fc, "-f", "%{family}\t%{file}", pattern],   # real tab separator in output
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 or "\t" not in proc.stdout:
        return None
    family_field, file_field = proc.stdout.split("\t", 1)
    # fc-match ALWAYS returns some font — only trust the resolution when the
    # family actually matches the request.
    if not _family_matches(face, family_field.split(",")):
        return None
    p = Path(file_field.strip())
    return p if p.is_file() else None


@functools.lru_cache(maxsize=64)
def _font_at_measure_size(path: str):
    try:
        from PIL import ImageFont
    except ImportError:
        return None
    try:
        return ImageFont.truetype(path, int(_MEASURE_SIZE))
    except Exception:
        return None


def line_width_pt(text: str, face: str, size_pt: float, *,
                  bold: bool = False) -> float | None:
    """Measured width of a single line in points. None -> caller falls back.
    Metrics scale linearly with size, so we measure once at _MEASURE_SIZE
    and scale — keeps the per-(path) font cache small."""
    f = find_font_file(face, bold=bold)
    if f is None:
        return None
    font = _font_at_measure_size(str(f))
    if font is None:
        return None
    return font.getlength(text) * (size_pt / _MEASURE_SIZE)


def avg_char_width_ratio(face: str, *, bold: bool = False) -> float | None:
    """Average glyph advance as a fraction of font size, measured from a
    representative sample — drop-in replacement for empirical ratio tables."""
    if os.environ.get("FEINSCHMIEDE_NO_REAL_METRICS") == "1":
        return None
    return _avg_char_width_ratio_cached(face, bold)


@functools.lru_cache(maxsize=256)
def _avg_char_width_ratio_cached(face: str, bold: bool) -> float | None:
    w = line_width_pt(_SAMPLE, face, _MEASURE_SIZE, bold=bold)
    if w is None:
        return None
    return (w / len(_SAMPLE)) / _MEASURE_SIZE
