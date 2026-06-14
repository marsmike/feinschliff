"""Mid-plan claim-evidence text gate.

Catches title-body-coherence and weak-evidence defects *before* render.
Works from a plan.yaml (pre-render) rather than a built .pptx.

Cheap text-only LLM judgment (~5 s for a 10-slide deck via Haiku)
replaces a full render+verify cycle for this defect class.

Usage
-----
From the pipeline (step 2b):

    from feinschliff.verify.deck.claim_evidence import judge_plan, write_report

    results = judge_plan(plan, design_brief=brief)
    overall = write_report(out_path, results, slide_count=len(plan["slides"]))

CLI:

    uv run feinschliff deck claim-evidence plan.yaml \\
      --design-brief design_brief.json -o claim_evidence_report.md

See skills/deck/references/pipeline.md §Step 2b.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from feinschliff.verify.llm import prompts
from feinschliff.verify.llm.rubric import _judge  # noqa: F401  (re-exported for patch targets)


# ---------------------------------------------------------------------------
# Constants — role classification
# ---------------------------------------------------------------------------

#: Roles that do NOT carry a claim (skip for this gate).
_NON_CLAIM_ROLES: frozenset[str] = frozenset({
    "title", "cover", "chapter", "agenda", "closer",
    "end", "quote", "divider",
})

#: Roles that explicitly carry a claim (judge them).
_CLAIM_ROLES: frozenset[str] = frozenset({
    "evidence", "recommendation", "resolution", "complication",
    "result", "claim", "data-quantity", "data-comparison",
    "content-columns", "content-with-visual",
})


# ---------------------------------------------------------------------------
# Public data class
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ClaimEvidenceResult:
    """Verdict for a single judged slide."""

    slide_index: int
    verdict: Literal["clean", "dirty"]
    rationale: str            # one-line LLM rationale
    suggested_title: str | None   # if title needs rewrite
    suggested_body: str | None    # if body needs evidence


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_slide_text(slide: dict) -> tuple[str, str]:
    """Return (title, body) extracted from a plan slide dict.

    Works from ``slide["content"]`` (inline) and falls back gracefully
    when expected slots are absent. Handles:

    - ``title`` — primary title slot
    - ``body``, ``supporting_body`` — prose body slots
    - ``bullets`` / ``bullets[]`` — list body slot (joined with newline)
    - ``subtitle`` — fallback body-like slot

    Returns empty strings for absent slots.
    """
    content: dict = slide.get("content", {}) or {}

    title: str = content.get("title", "") or ""

    body_parts: list[str] = []

    for key in ("body", "supporting_body"):
        val = content.get(key)
        if val and str(val).strip():
            body_parts.append(str(val).strip())

    bullets = content.get("bullets")
    if bullets:
        if isinstance(bullets, list):
            items = [str(b).strip() for b in bullets if b]
            if items:
                body_parts.append("\n".join(f"• {b}" for b in items))
        elif str(bullets).strip():
            body_parts.append(str(bullets).strip())

    # subtitle goes into body when there's no other body content
    subtitle = content.get("subtitle")
    if subtitle and str(subtitle).strip() and not body_parts:
        body_parts.append(str(subtitle).strip())

    return title.strip(), "\n\n".join(body_parts)


def _has_claim_role(slide: dict, brief_slide: dict | None) -> bool:
    """Return True when the slide should be judged (has a claim role).

    Priority:
    1. ``design_brief.slides[i].role`` (authoritative design-brief role)
    2. ``slide._meta.role`` (plan-embedded role)
    3. Default to True (unknown role → judge it)
    """
    # Design brief wins if present
    if brief_slide is not None:
        role = (brief_slide.get("role") or "").strip().lower()
        if role:
            return role not in _NON_CLAIM_ROLES

    # Fall back to _meta.role in the plan slide
    meta = slide.get("_meta") or {}
    role = (meta.get("role") or "").strip().lower()
    if role:
        return role not in _NON_CLAIM_ROLES

    # No role specified — default to judging
    return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def judge_plan(
    plan: dict,
    design_brief: dict | None = None,
    *,
    offline: bool = False,
    model: str = "claude-haiku-4-5-20251001",
) -> list[ClaimEvidenceResult]:
    """Judge each claim-carrying slide in *plan* for title-body coherence.

    For each slide where the role implies a claim, calls Haiku with the
    slide's title + body text and (if available) the target claim from
    ``design_brief.slides[i].claim``.

    Two questions per slide:
    1. Does the body provide evidence for the title's claim?
    2. Is there content in the body unrelated to the title?

    Returns one :class:`ClaimEvidenceResult` per slide judged. Slides
    whose role is non-claim (chapter, agenda, closer, etc.) are skipped
    and not included in the returned list.

    When *offline* is ``True``, returns ``"clean"`` verdicts with a
    ``"skipped: offline"`` rationale and no API calls.
    """
    slides: list[dict] = plan.get("slides") or []
    brief_slides: list[dict] = (design_brief or {}).get("slides") or []

    results: list[ClaimEvidenceResult] = []

    for idx, slide in enumerate(slides):
        brief_slide = brief_slides[idx] if idx < len(brief_slides) else None

        if not _has_claim_role(slide, brief_slide=brief_slide):
            continue

        if offline:
            results.append(ClaimEvidenceResult(
                slide_index=idx + 1,
                verdict="clean",
                rationale="skipped: offline",
                suggested_title=None,
                suggested_body=None,
            ))
            continue

        title, body = _extract_slide_text(slide)
        target_claim: str | None = None
        if brief_slide is not None:
            target_claim = brief_slide.get("claim") or None

        prompt = prompts.claim_evidence_prompt(title, body, target_claim=target_claim)
        raw = _judge(prompt, model=model)

        if "verdict" not in raw and raw.get("status") == "fail":
            results.append(ClaimEvidenceResult(
                slide_index=idx + 1,
                verdict="dirty",
                rationale=f"[judgment error] {raw.get('reason', 'unparseable response')}",
                suggested_title=None,
                suggested_body=None,
            ))
            continue

        verdict: Literal["clean", "dirty"] = (
            "dirty" if str(raw.get("verdict", "")).lower() == "dirty" else "clean"
        )
        results.append(ClaimEvidenceResult(
            slide_index=idx + 1,
            verdict=verdict,
            rationale=str(raw.get("rationale", raw.get("reason", ""))),
            suggested_title=raw.get("suggested_title") or None,
            suggested_body=raw.get("suggested_body") or None,
        ))

    return results


def write_report(
    path: Path,
    results: list[ClaimEvidenceResult],
    *,
    slide_count: int,
) -> Literal["clean", "dirty"]:
    """Write a markdown claim-evidence report to *path*.

    The header matches the style of ``storyline_report.md``
    (see :mod:`feinschliff.verify.deck.storyline`).

    Returns the overall verdict: ``"clean"`` if every result is clean,
    ``"dirty"`` if any result is dirty.
    """
    overall: Literal["clean", "dirty"] = (
        "dirty" if any(r.verdict == "dirty" for r in results) else "clean"
    )

    judged = len(results)
    dirty_count = sum(1 for r in results if r.verdict == "dirty")

    parts: list[str] = [
        "# Claim-Evidence Report",
        "",
        f"- Verdict: {overall}",
        f"- Slides judged: {judged}",
        f"- Slides total: {slide_count}",
        "",
        "---",
        "",
    ]

    if not results:
        parts.append("_(no claim-bearing slides to judge)_")
    else:
        parts.append("## Per-slide results")
        parts.append("")
        for r in results:
            status_icon = "clean" if r.verdict == "clean" else "DIRTY"
            parts.append(f"**Slide {r.slide_index}** — {status_icon}")
            parts.append(f"- Rationale: {r.rationale}")
            if r.suggested_title:
                parts.append(f"- Suggested title: {r.suggested_title}")
            if r.suggested_body:
                parts.append(f"- Suggested body: {r.suggested_body}")
            parts.append("")

    if overall == "dirty":
        parts.append(f"## Summary — {dirty_count} slide(s) need attention")
        parts.append("")
        for r in results:
            if r.verdict == "dirty":
                parts.append(f"- Slide {r.slide_index}: {r.rationale}")
        parts.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n")
    return overall
