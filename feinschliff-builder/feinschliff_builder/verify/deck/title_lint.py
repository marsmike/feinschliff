"""Deterministic title-lint rules. Zero LLM.

Catches common title defects: topic labels (no verb), overly long titles,
conjunction splits, and empty titles. Returns a list of :class:`TitleLintIssue`
objects — one per violation found.

Usage
-----
From the pipeline (step 1d):

    from feinschliff_builder.verify.deck.title_lint import lint_titles

    issues = lint_titles(titles)

CLI:

    feinschliff deck title-lint plan.yaml -o title_lint_report.md [--json]
"""
from __future__ import annotations

import re
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Public data class
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TitleLintIssue:
    """A single title-lint violation."""

    slide: int     # 1-based slide number
    rule: str      # short slug, e.g. "title-too-long"
    severity: str  # "warn" | "fail"
    message: str


# ---------------------------------------------------------------------------
# Rule helpers
# ---------------------------------------------------------------------------

#: Common English finite-verb irregular forms (lower-case).
_IRREGULAR_VERBS: frozenset[str] = frozenset({
    "is", "are", "was", "were",
    "has", "have", "had",
    "will", "shall", "can", "may", "must",
    "do", "does", "did",
    "drive", "drives", "drove",
    "grow", "grew",
    "win", "wins", "won",
    "lose", "loses", "lost",
    "ship", "ships", "shipped",
    "build", "builds", "built",
})

#: Regex: a word of 4+ chars ending in a common finite-verb suffix.
_VERB_SUFFIX_RE = re.compile(r"\b[a-z]{3}[a-z]*(s|ed|ing)\b")

#: Regex: standalone " and " (whitespace-bounded, case-insensitive).
_AND_RE = re.compile(r"(?i)\band\b")


def _has_verb(title: str) -> bool:
    """Return True when the title appears to contain a finite verb.

    Strategy:
    1. Check the irregular-verb whitelist (exact word match).
    2. Check for any word with a verb-like suffix (≥4 chars ending in s/ed/ing),
       excluding purely numeric or all-uppercase tokens (acronyms).
    """
    words = title.split()
    for word in words:
        clean = re.sub(r"[^a-zA-Z0-9]", "", word)
        if not clean:
            continue
        # Skip purely numeric tokens
        if clean.isdigit():
            continue
        # Skip all-uppercase tokens (acronyms like AI, CEO, SaaS are not verbs)
        if clean.isupper() and len(clean) > 1:
            continue
        lower = clean.lower()
        if lower in _IRREGULAR_VERBS:
            return True
        if _VERB_SUFFIX_RE.match(lower):
            return True
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def lint_titles(titles: list[str]) -> list[TitleLintIssue]:
    """Apply deterministic lint rules to a sequence of slide titles.

    Returns a list of :class:`TitleLintIssue` objects, one per violation.
    A clean deck returns an empty list.

    Rules (by slug):
    - ``title-empty``           — title is blank or whitespace-only (fail)
    - ``title-too-long``        — 16-20 words: warn; 21+ words: fail
    - ``title-no-verb``         — no finite verb detected (warn)
    - ``title-and-conjunction`` — contains standalone "and" (warn — split candidate)
    """
    issues: list[TitleLintIssue] = []

    for idx, title in enumerate(titles, start=1):
        stripped = title.strip() if title else ""

        # Rule: title-empty
        if not stripped:
            issues.append(TitleLintIssue(
                slide=idx,
                rule="title-empty",
                severity="fail",
                message=f"Slide {idx}: title is empty.",
            ))
            continue  # no further rules make sense for empty titles

        word_count = len(stripped.split())

        # Rule: title-too-long
        if word_count >= 21:
            issues.append(TitleLintIssue(
                slide=idx,
                rule="title-too-long",
                severity="fail",
                message=(
                    f"Slide {idx}: title has {word_count} words "
                    f"(21+ is a fail; trim to ≤15 words)."
                ),
            ))
        elif word_count >= 16:
            issues.append(TitleLintIssue(
                slide=idx,
                rule="title-too-long",
                severity="warn",
                message=(
                    f"Slide {idx}: title has {word_count} words "
                    f"(16-20 is a warning; aim for ≤15 words)."
                ),
            ))

        # Rule: title-no-verb
        if not _has_verb(stripped):
            issues.append(TitleLintIssue(
                slide=idx,
                rule="title-no-verb",
                severity="warn",
                message=(
                    f"Slide {idx}: title appears to contain no finite verb "
                    f"— topic label rather than a claim? "
                    f"(\"{stripped}\")"
                ),
            ))

        # Rule: title-and-conjunction
        if _AND_RE.search(stripped):
            issues.append(TitleLintIssue(
                slide=idx,
                rule="title-and-conjunction",
                severity="warn",
                message=(
                    f"Slide {idx}: title contains \"and\" — "
                    f"consider splitting into two slides."
                ),
            ))

    return issues
