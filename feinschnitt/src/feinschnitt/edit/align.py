"""Speech-anchor alignment — the word-level timing backbone.

A speech_anchor marks WHEN a visual appears: the beat snaps to the anchor's
word boundaries in words.json. Invariants (locked):
- the authored end_sec is NEVER shortened, only extended;
- non-sequence kinds cap extensions at MAX_BEAT past start (visuals beyond
  ~5s read as boring static frames; close_gaps may add ≤MAX_GAP when bridging);
- output is a DERIVED list; the authored plan file is never mutated.
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from feinschnitt.edit import EditError
from feinschnitt.edit.lint import SEQUENCE_KINDS

LEAD = 0.10      # visual leads the first word slightly
TAIL = 0.80      # punctuation dwell past the last word (not boring)
MAX_BEAT = 5.0   # soft ceiling for non-sequence single visuals (close_gaps may add ≤MAX_GAP when bridging)
MAX_GAP = 0.50   # bridge micro-gaps (flicker frames); larger = intentional air
MIN_SCORE = 0.7  # ordered-token overlap needed for a fuzzy anchor match

_DE_FOLD = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def _norm(token: str) -> str:
    t = token.casefold().translate(_DE_FOLD)
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", t)


def find_anchor(words: list[dict], anchor: str,
                near: float | None = None) -> tuple[int, int] | None:
    """Best window of len(anchor-tokens) with >=MIN_SCORE positional overlap.

    Equal-score windows (a repeated phrase / refrain) are disambiguated by
    proximity to `near` — the authored start_sec is the author's intent for
    WHICH occurrence is meant.
    """
    tokens = [t for t in (_norm(t) for t in anchor.split()) if t]
    if not tokens:
        return None
    normed = [_norm(w["w"]) for w in words]
    best: tuple[float, float, int, int] | None = None
    for i in range(max(0, len(words) - len(tokens) + 1)):
        window = normed[i:i + len(tokens)]
        score = sum(1 for a, b in zip(tokens, window) if a and a == b) / len(tokens)
        if score < MIN_SCORE:
            continue
        closeness = -abs(words[i]["s"] - near) if near is not None else 0.0
        rank = (score, closeness)
        if best is None or rank > (best[0], best[1]):
            best = (score, closeness, i, i + len(tokens) - 1)
    return (best[2], best[3]) if best else None


def align_beats(beats: list[dict], words: list[dict],
                duration: float | None = None) -> list[dict]:
    out = []
    for beat in beats:
        b = dict(beat)
        anchor = b.get("speech_anchor")
        if anchor:
            authored_start = b.get("start_sec")
            near = (float(authored_start)
                    if isinstance(authored_start, (int, float))
                    and not isinstance(authored_start, bool) else None)
            span = find_anchor(words, anchor, near=near)
            if span is None:
                b["_align"] = "anchor-not-found"
            else:
                i, j = span
                b["start_sec"] = round(max(0.0, words[i]["s"] - LEAD), 3)
                authored_end = float(b.get("end_sec", 0.0))
                new_end = max(authored_end, words[j]["e"] + TAIL)
                if b.get("kind") not in SEQUENCE_KINDS and new_end > authored_end:
                    new_end = max(authored_end,
                                  min(new_end, b["start_sec"] + MAX_BEAT))
                if duration is not None and new_end > authored_end:
                    new_end = max(authored_end, min(new_end, duration))
                b["end_sec"] = round(new_end, 3)
                b["_align"] = "ok"
        out.append(b)
    return out


def close_gaps(beats: list[dict], max_gap: float = MAX_GAP) -> list[dict]:
    ordered = sorted((dict(b) for b in beats), key=lambda b: b["start_sec"])
    for prev, nxt in zip(ordered, ordered[1:]):
        gap = nxt["start_sec"] - prev["end_sec"]
        if 0 < gap <= max_gap:
            prev["end_sec"] = nxt["start_sec"]
    return ordered


def run(plan: dict, words_path: Path, out_path: Path) -> dict:
    try:
        data = json.loads(words_path.read_text())
        words = data["words"]
        duration = float(data.get("duration", 0.0)) or None
    except FileNotFoundError as exc:
        raise EditError(f"words.json not found: {words_path} — run transcribe "
                        "first") from exc
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise EditError(f"words.json invalid: {words_path} ({exc})") from exc
    aligned = dict(plan)
    aligned["beats"] = close_gaps(align_beats(plan["beats"], words, duration))
    out_path.write_text(json.dumps(aligned, indent=2))
    return aligned
