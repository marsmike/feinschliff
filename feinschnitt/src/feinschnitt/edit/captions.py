"""Caption generation — word-synced chunks derived from words.json.

Captions are GENERATED, never authored (plan config: enabled + emphasis only).
Suppression model: takeover/text beats are mutually exclusive with captions
(literal window drop); visual overlays keep captions unless they semantically
echo the beat; every beat gets a ±0.8s semantic echo pad (stopword-filtered
meaningful-word overlap — Luuk's layered-text rule, adapted)."""
from __future__ import annotations

from feinschnitt.edit.align import _norm
from feinschnitt.edit.lint import KNOWN_KINDS

MAX_WORDS_PORTRAIT = 3
MAX_WORDS_LANDSCAPE = 5
CHUNK_GAP = 0.5          # inter-word silence that forces a chunk break
CHUNK_TAIL = 0.4         # display tail after the last word (capped by next chunk)
ECHO_PAD = 0.8           # semantic lead/tail pad around every beat

CAPTION_SUPPRESSING_KINDS = {"stat_punch", "quote_pull", "static",
                             "vertical_timeline", "word_pop", "hook_title"}
CAPTION_FRIENDLY_KINDS = {"image_card", "ratio_dots", "inline_chart"}
assert CAPTION_SUPPRESSING_KINDS | CAPTION_FRIENDLY_KINDS == KNOWN_KINDS, (
    "new kind must be classified in CAPTION_SUPPRESSING_KINDS or "
    "CAPTION_FRIENDLY_KINDS"
)

STOPWORDS = {  # en + de function words — meaningful-word overlap only
    "the", "a", "an", "and", "or", "but", "of", "in", "on", "at", "to", "for",
    "with", "by", "is", "was", "are", "were", "be", "been", "it", "its", "my",
    "your", "our", "their", "this", "that", "these", "those", "i", "you", "he",
    "she", "we", "they", "not", "no", "so", "as", "if", "then", "than", "too",
    "der", "die", "das", "ein", "eine", "und", "oder", "aber", "von", "im",
    "in", "an", "auf", "zu", "fur", "mit", "bei", "ist", "war", "sind", "es",
    "ich", "du", "wir", "sie", "nicht", "kein", "so", "als", "wenn", "dann",
    # contraction norms (apostrophes stripped by _norm)
    "dont", "doesnt", "didnt", "isnt", "arent", "wasnt", "werent",
    "thats", "youre", "theyre", "weve", "ive", "whats",
    # auxiliaries
    "do", "does", "did", "have", "has", "had", "will", "would", "can",
    "could", "should", "im", "am",
    # German wh-words / conjunctions
    "wie", "wer", "wo", "dass", "weil", "auch", "noch", "nur", "schon", "mal",
}


def beat_text_tokens(beat: dict) -> set[str]:
    """Normalized meaningful tokens across every text-bearing beat field.
    Extend when a new kind adds a text field (mirror of the TS-side rule)."""
    parts: list[str] = []
    for key in ("title", "kicker", "value", "caption", "quote_text",
                "attribution"):
        v = beat.get(key)
        if isinstance(v, (str, int, float)) and not isinstance(v, bool):
            parts.append(str(v))
    for item in beat.get("items") or []:
        if isinstance(item, dict):
            parts.append(str(item.get("text") or ""))
    for step in beat.get("steps") or []:
        if isinstance(step, dict):
            parts.append(str(step.get("heading") or ""))
            parts.append(str(step.get("description") or ""))
    for label in beat.get("labels") or []:
        parts.append(str(label))
    tokens = set()
    for part in parts:
        for tok in part.replace("\\n", " ").split():
            n = _norm(tok)
            if n and n not in STOPWORDS:
                tokens.add(n)
    return tokens


def chunk_words(words: list[dict], max_words: int) -> list[dict]:
    """Group transcript words into display chunks (D-M3-4)."""
    chunks: list[list[dict]] = []
    current: list[dict] = []
    for word in words:
        if current:
            gap = word["s"] - current[-1]["e"]
            ended = current[-1]["w"].rstrip().endswith((".", "?", "!"))
            if len(current) >= max_words or gap >= CHUNK_GAP or ended:
                chunks.append(current)
                current = []
        current.append(word)
    if current:
        chunks.append(current)
    out = []
    for i, chunk in enumerate(chunks):
        end = chunk[-1]["e"] + CHUNK_TAIL
        if i + 1 < len(chunks):
            end = min(end, chunks[i + 1][0]["s"])
        out.append({"s": round(chunk[0]["s"], 3), "e": round(end, 3),
                    "words": [{"w": w["w"], "s": w["s"], "e": w["e"],
                               "accent": False} for w in chunk]})
    return out


def _overlaps(chunk: dict, lo: float, hi: float) -> bool:
    """True when the chunk's DISPLAY window [s, e] intersects [lo, hi).

    The display window includes the 0.4s tail, so a chunk whose tail pokes
    into a takeover window is dropped whole — no caption lingering under a
    takeover entrance.
    """
    return chunk["s"] < hi and chunk["e"] > lo


def _chunk_tokens(chunk: dict) -> set[str]:
    return {n for w in chunk["words"]
            if (n := _norm(w["w"])) and n not in STOPWORDS}


def suppress(chunks: list[dict], beats: list[dict]) -> list[dict]:
    """Drop chunks per D-M3-2. Beats with invalid timing are skipped."""
    kept = []
    for chunk in chunks:
        dead = False
        ctokens = _chunk_tokens(chunk)
        for b in beats:
            kind = b.get("kind")
            start, end = b.get("start_sec"), b.get("end_sec")
            if not isinstance(start, (int, float)) or isinstance(start, bool):
                continue
            if not isinstance(end, (int, float)) or isinstance(end, bool):
                continue
            btokens = None
            if _overlaps(chunk, start, end):
                if kind in CAPTION_SUPPRESSING_KINDS:
                    dead = True
                    break
                # friendly kind — only drop on semantic echo
                btokens = beat_text_tokens(b)
                if ctokens & btokens:
                    dead = True
                    break
            elif _overlaps(chunk, start - ECHO_PAD, end + ECHO_PAD):
                # pad window only (mutually exclusive from the literal window)
                btokens = beat_text_tokens(b)
                if ctokens & btokens:
                    dead = True
                    break
        if not dead:
            kept.append(chunk)
    return kept


def _match_phrase_runs(chunks: list[dict], normalized: list[list[str]]) -> list[bool]:
    """Return a matched[i] bool for each phrase in *normalized* against *chunks*."""
    matched = [False] * len(normalized)
    for chunk in chunks:
        cnorm = [_norm(w["w"]) for w in chunk["words"]]
        for pi, ptoks in enumerate(normalized):
            if not ptoks:
                continue
            for i in range(len(cnorm) - len(ptoks) + 1):
                if cnorm[i:i + len(ptoks)] == ptoks:
                    matched[pi] = True
    return matched


def apply_emphasis(chunks: list[dict],
                   phrases: list[str]) -> tuple[list[dict], list[str]]:
    """Mark emphasis-phrase word runs accent=True; return unmatched phrases."""
    normalized = [[t for t in (_norm(p) for p in phrase.split()) if t]
                  for phrase in phrases]
    matched = [False] * len(phrases)
    for chunk in chunks:
        cnorm = [_norm(w["w"]) for w in chunk["words"]]
        for pi, ptoks in enumerate(normalized):
            if not ptoks:
                continue
            for i in range(len(cnorm) - len(ptoks) + 1):
                if cnorm[i:i + len(ptoks)] == ptoks:
                    for j in range(i, i + len(ptoks)):
                        chunk["words"][j]["accent"] = True
                    matched[pi] = True
    unmatched = [phrases[i] for i, m in enumerate(matched) if not m]
    return chunks, unmatched


def build_captions(words: list[dict], beats: list[dict], config: dict | None,
                   width: int, height: int) -> tuple[list[dict], list[str]]:
    """words.json + aligned beats + plan config -> (chunks, warnings).

    Two-pass emphasis bookkeeping:
      Pass 1 — match phrases against ALL chunks (pre-suppression) to learn
               which phrases actually appear anywhere in the transcript.
      Pass 2 — apply_emphasis only on the kept (post-suppression) chunks
               and produces the accent flags; re-check which phrases still
               match inside kept chunks to distinguish the two warning cases.

    Warning messages:
      "emphasis phrase not found in transcript: {p!r}"
          — phrase never matched any word run, pre-suppression.
      "emphasis phrase {p!r} only occurs in caption chunks suppressed by a
       beat (or split across chunks) — it will not render"
          — phrase WAS spoken (matched pre-suppression) but is absent from
            every kept chunk (suppression swallowed every occurrence).
    """
    cfg = config or {}
    if cfg.get("enabled", True) is False:
        return [], []
    max_words = MAX_WORDS_LANDSCAPE if width > height else MAX_WORDS_PORTRAIT
    all_chunks = chunk_words(words, max_words)
    kept_chunks = suppress(all_chunks, beats)
    phrases = cfg.get("emphasis") or []
    phrases = [p for p in phrases if isinstance(p, str)]
    if not phrases:
        return kept_chunks, []

    normalized = [[t for t in (_norm(p) for p in phrase.split()) if t]
                  for phrase in phrases]

    # Pass 1: did the phrase appear ANYWHERE in the transcript (pre-suppression)?
    spoken = _match_phrase_runs(all_chunks, normalized)

    # Pass 2: mark accents on kept chunks; learn which survive suppression.
    kept_chunks, _ = apply_emphasis(kept_chunks, phrases)
    surviving = _match_phrase_runs(kept_chunks, normalized)

    warnings: list[str] = []
    for pi, phrase in enumerate(phrases):
        if not spoken[pi]:
            warnings.append(
                f"captions: emphasis phrase not found in transcript: {phrase!r}"
            )
        elif not surviving[pi]:
            warnings.append(
                f"captions: emphasis phrase {phrase!r} only occurs in caption "
                "chunks suppressed by a beat (or split across chunks) — it "
                "will not render"
            )
    return kept_chunks, warnings
