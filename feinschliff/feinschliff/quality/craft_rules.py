"""Deterministic Knaflic-style craft-rules checker. Zero LLM.

Evaluates a list of slide dicts (each with ``layout`` and ``content_inline``
or ``content`` keys) against a set of data-storytelling rules derived from
Cole Nussbaumer Knaflic's principles.  All checks are structural — they
inspect layout names and content field values only; no rendering is required.

Public API
----------
check_craft_rules(slides, *, brand_palette=None) -> CraftReport
write_craft_report(report, path) -> None
"""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Public data classes
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class CraftIssue:
    slide: int        # 1-based; 0 for deck-level
    rule: str         # short slug
    severity: str     # "warn" | "fail"
    message: str
    meta: dict        # rule-specific context


@dataclasses.dataclass(frozen=True)
class CraftReport:
    verdict: str              # "clean" | "warn" | "fail"
    issues: list[CraftIssue]


# ---------------------------------------------------------------------------
# Verb detection — delegate to feinschliff_builder when available
# ---------------------------------------------------------------------------

def _try_import_has_verb():
    """Return the _has_verb function from title_lint, or None on ImportError."""
    try:
        from feinschliff_builder.verify.deck.title_lint import (  # type: ignore[import]
            _has_verb,
        )
        return _has_verb
    except (ImportError, AttributeError):
        return None


def _build_inline_has_verb():
    """Inline fallback — mirrors the logic in title_lint._has_verb."""
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
    _VERB_SUFFIX_RE = re.compile(r"\b[a-z]{3}[a-z]*(s|ed|ing)\b")

    def _has_verb(title: str) -> bool:
        words = title.split()
        for word in words:
            clean = re.sub(r"[^a-zA-Z0-9]", "", word)
            if not clean:
                continue
            if clean.isdigit():
                continue
            if clean.isupper() and len(clean) > 1:
                continue
            lower = clean.lower()
            if lower in _IRREGULAR_VERBS:
                return True
            if _VERB_SUFFIX_RE.match(lower):
                return True
        return False

    return _has_verb


# Resolve once at import time.
_has_verb = _try_import_has_verb() or _build_inline_has_verb()

# ---------------------------------------------------------------------------
# Layout-name helpers
# ---------------------------------------------------------------------------

_CHART_LAYOUTS: frozenset[str] = frozenset({
    "bar-chart", "line-chart", "stacked-bar", "waterfall", "kpi-grid", "scorecard",
})

_TOKEN_RE = re.compile(r"\$[a-z][a-z0-9-]*")
_AND_RE = re.compile(r"(?<!\S)and(?!\S)", re.IGNORECASE)


def _layout_stem(layout: str) -> str:
    """Return the bare stem from a layout path like '.../bar-chart.slide.dsl'."""
    stem = Path(layout).name
    for suffix in (".slide.dsl", ".dsl"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return stem


def _get_title(content: dict[str, Any]) -> str:
    """Extract title text from a content dict."""
    for key in ("title", "action_title"):
        val = content.get(key)
        if val and isinstance(val, str):
            return val.strip()
    return ""


def _body_words(content: dict[str, Any]) -> int:
    """Sum word count across body / bullets / so_what / subtitle fields."""
    total = 0
    for key in ("body", "bullets", "so_what", "subtitle"):
        val = content.get(key)
        if not val:
            continue
        if isinstance(val, str):
            total += len(val.split())
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    total += len(item.split())
                elif isinstance(item, dict):
                    for v in item.values():
                        if isinstance(v, str):
                            total += len(v.split())
    return total


def _collect_token_refs(content: dict[str, Any]) -> set[str]:
    """Collect distinct $token references from all string values in content."""
    found: set[str] = set()

    def _walk(obj: Any) -> None:
        if isinstance(obj, str):
            found.update(_TOKEN_RE.findall(obj))
        elif isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    _walk(content)
    return found


# ---------------------------------------------------------------------------
# Per-rule checkers
# ---------------------------------------------------------------------------

def _check_no_pie(slide_num: int, stem: str) -> CraftIssue | None:
    if stem.startswith("pie-chart") or "donut" in stem:
        return CraftIssue(
            slide=slide_num,
            rule="no-pie-chart",
            severity="fail",
            message=(
                "Pie/donut charts are forbidden (Knaflic): use a bar chart "
                "with sorted categories instead."
            ),
            meta={"layout_stem": stem},
        )
    return None


def _check_no_3d(slide_num: int, stem: str) -> CraftIssue | None:
    if stem.endswith("-3d"):
        return CraftIssue(
            slide=slide_num,
            rule="no-3d-chart",
            severity="fail",
            message="3-D charts distort perception — use a flat equivalent.",
            meta={"layout_stem": stem},
        )
    return None


def _check_title_word_count(slide_num: int, title: str) -> CraftIssue | None:
    if not title:
        return None
    wc = len(title.split())
    if wc >= 21:
        return CraftIssue(
            slide=slide_num,
            rule="title-word-count",
            severity="fail",
            message=f"Title has {wc} words (≥21 is a fail; trim to ≤15).",
            meta={"word_count": wc},
        )
    if wc >= 16:
        return CraftIssue(
            slide=slide_num,
            rule="title-word-count",
            severity="warn",
            message=f"Title has {wc} words (16-20 is a warning; aim for ≤15).",
            meta={"word_count": wc},
        )
    return None


def _check_body_word_count(slide_num: int, content: dict[str, Any]) -> CraftIssue | None:
    wc = _body_words(content)
    if wc > 80:
        return CraftIssue(
            slide=slide_num,
            rule="body-word-count",
            severity="fail",
            message=f"Body text has {wc} words (>80 is a fail; aim for ≤50).",
            meta={"word_count": wc},
        )
    if wc > 50:
        return CraftIssue(
            slide=slide_num,
            rule="body-word-count",
            severity="warn",
            message=f"Body text has {wc} words (51-80 is a warning; aim for ≤50).",
            meta={"word_count": wc},
        )
    return None


def _check_title_contains_and(slide_num: int, title: str) -> CraftIssue | None:
    if not title:
        return None
    if _AND_RE.search(title):
        return CraftIssue(
            slide=slide_num,
            rule="title-contains-and",
            severity="warn",
            message="Title contains 'and' — candidate two-slide split.",
            meta={"title": title},
        )
    return None


def _check_title_not_claim(slide_num: int, title: str) -> CraftIssue | None:
    if not title:
        return None
    if not _has_verb(title):
        return CraftIssue(
            slide=slide_num,
            rule="title-not-claim",
            severity="warn",
            message=(
                f"Title appears to contain no finite verb — topic label "
                f"rather than a claim? (\"{title}\")"
            ),
            meta={"title": title},
        )
    return None


def _check_chart_title_claim(slide_num: int, stem: str, title: str) -> CraftIssue | None:
    if stem not in _CHART_LAYOUTS:
        return None
    if not title:
        return CraftIssue(
            slide=slide_num,
            rule="chart-title-claim",
            severity="warn",
            message=(
                f"Chart slide (layout: {stem}) has no title — chart titles "
                "should state a claim, not be omitted."
            ),
            meta={"layout_stem": stem},
        )
    if not _has_verb(title):
        return CraftIssue(
            slide=slide_num,
            rule="chart-title-claim",
            severity="warn",
            message=(
                f"Chart title \"{title}\" is a topic label, not a claim "
                f"(layout: {stem})."
            ),
            meta={"layout_stem": stem, "title": title},
        )
    return None


def _check_too_many_colors(
    slide_num: int,
    content: dict[str, Any],
    brand_palette: list[str],
) -> CraftIssue | None:
    refs = _collect_token_refs(content)
    # Only count refs that appear in the brand palette (or all refs when palette
    # is an empty list — treat that as "count everything").
    if brand_palette:
        palette_set = set(brand_palette)
        counted = {r for r in refs if r in palette_set}
    else:
        counted = refs
    if len(counted) > 4:
        return CraftIssue(
            slide=slide_num,
            rule="too-many-colors",
            severity="warn",
            message=(
                f"Slide references {len(counted)} distinct color tokens "
                f"(>{4} is a warning; limit to 4 for visual coherence)."
            ),
            meta={"token_count": len(counted), "tokens": sorted(counted)},
        )
    return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def check_craft_rules(
    slides: list[dict],
    *,
    brand_palette: list[str] | None = None,
) -> CraftReport:
    """Check a list of slide dicts against Knaflic craft rules.

    Parameters
    ----------
    slides:
        Each dict must have a ``layout`` key (path string) and optionally
        ``content_inline`` or ``content`` (dict of field values).
    brand_palette:
        Optional list of ``$token`` strings representing the brand's palette.
        When supplied, ``too-many-colors`` counts only tokens in this list.
        Pass an empty list to count all ``$token`` references.
        Pass ``None`` to skip the rule entirely.

    Returns
    -------
    CraftReport
        ``verdict`` is ``"fail"`` if any issue has severity ``"fail"``,
        ``"warn"`` if any has ``"warn"``, otherwise ``"clean"``.
    """
    issues: list[CraftIssue] = []

    for idx, slide in enumerate(slides, start=1):
        layout = slide.get("layout", "")
        stem = _layout_stem(layout)
        content: dict[str, Any] = slide.get("content_inline") or slide.get("content") or {}

        title = _get_title(content)

        # Rule: no-pie-chart
        issue = _check_no_pie(idx, stem)
        if issue:
            issues.append(issue)

        # Rule: no-3d-chart
        issue = _check_no_3d(idx, stem)
        if issue:
            issues.append(issue)

        # Rule: title-word-count
        issue = _check_title_word_count(idx, title)
        if issue:
            issues.append(issue)

        # Rule: body-word-count
        issue = _check_body_word_count(idx, content)
        if issue:
            issues.append(issue)

        # Rule: title-contains-and
        issue = _check_title_contains_and(idx, title)
        if issue:
            issues.append(issue)

        # Rule: title-not-claim
        issue = _check_title_not_claim(idx, title)
        if issue:
            issues.append(issue)

        # Rule: chart-title-claim
        issue = _check_chart_title_claim(idx, stem, title)
        if issue:
            issues.append(issue)

        # Rule: too-many-colors (only when brand_palette is supplied)
        if brand_palette is not None:
            issue = _check_too_many_colors(idx, content, brand_palette)
            if issue:
                issues.append(issue)

    # Compute verdict
    if any(i.severity == "fail" for i in issues):
        verdict = "fail"
    elif any(i.severity == "warn" for i in issues):
        verdict = "warn"
    else:
        verdict = "clean"

    return CraftReport(verdict=verdict, issues=issues)
