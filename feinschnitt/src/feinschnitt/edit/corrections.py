"""Correction memory — deterministic patches for known Whisper mishearings.

When a mistranscription shows up in a render, DO NOT hand-fix words.json;
add the entry here so every future video is fixed (doctrine: every
correction becomes a table row, dated in the commit message).

Tokens may carry leading/trailing whitespace or punctuation; matching uses
the stripped core and punctuation is preserved around replacements.
"""
from __future__ import annotations

# Single-token map (case-insensitive key → canonical replacement).
# Capitalization of the heard token is preserved on the replacement.
BRAND_WORDS: dict[str, str] = {
    "cloud": "Claude",
    "clod": "Claude",
}

# Multi-token runs → replacement tokens. Timing of the run is preserved:
# the replacement tokens split the original [first.s, last.e] span evenly.
# List longer phrases before any entry that is their prefix (first match wins).
PHRASE_CORRECTIONS: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    (("fine", "schnitt"), ("feinschnitt",)),
    (("fine", "schliff"), ("feinschliff",)),
    (("fine", "schmiede"), ("feinschmiede",)),
    (("fine", "klang"), ("feinklang",)),
    (("fine", "bild"), ("feinbild",)),
]

def fingerprint() -> str:
    """Cache fingerprint of the correction tables — transcription caches must
    invalidate when a table row is added (the correction-memory workflow)."""
    import hashlib
    payload = repr((sorted(BRAND_WORDS.items()), PHRASE_CORRECTIONS))
    return hashlib.sha1(payload.encode()).hexdigest()[:12]


_PUNCT = ".,!?;:"


def _split(token: str) -> tuple[str, str, str]:
    """(prefix, core, suffix) — punctuation around the whitespace-stripped core."""
    core = token.strip()
    prefix = ""
    suffix = ""
    while core and core[0] in _PUNCT:
        prefix += core[0]
        core = core[1:]
    while core and core[-1] in _PUNCT:
        suffix = core[-1] + suffix
        core = core[:-1]
    return prefix, core, suffix


def _core(token: str) -> str:
    return _split(token)[1].lower()


def _match_case(heard: str, replacement: str) -> str:
    if heard.isupper():
        return replacement.upper()
    if heard[:1].isupper():
        return replacement[:1].upper() + replacement[1:]
    return replacement.lower()


def apply_corrections(words: list[dict]) -> list[dict]:
    # Pass 1: single brand words.
    staged = []
    for word in words:
        token = dict(word)
        prefix, core, suffix = _split(token["w"])
        repl = BRAND_WORDS.get(core.lower())
        if repl:
            token["w"] = prefix + _match_case(core, repl) + suffix
        staged.append(token)

    # Pass 2: phrase runs.
    out: list[dict] = []
    i = 0
    while i < len(staged):
        for wrong, right in PHRASE_CORRECTIONS:
            n = len(wrong)
            if tuple(_core(t["w"]) for t in staged[i:i + n]) == wrong:
                start, end = staged[i]["s"], staged[i + n - 1]["e"]
                first_prefix = _split(staged[i]["w"])[0]
                last_suffix = _split(staged[i + n - 1]["w"])[2]
                step = (end - start) / len(right)
                for k, tok in enumerate(right):
                    p = first_prefix if k == 0 else ""
                    s = last_suffix if k == len(right) - 1 else ""
                    out.append({"w": p + tok + s,
                                "s": round(start + k * step, 3),
                                "e": round(start + (k + 1) * step, 3)})
                i += n
                break
        else:
            out.append(staged[i])
            i += 1
    return out
