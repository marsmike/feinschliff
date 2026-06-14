"""Prompt templates for LLM defect classes."""
from __future__ import annotations


def squint_prompt(thumbnail_b64: str) -> str:
    return (
        "You are judging a 25%-scale thumbnail of a slide. At this size, "
        "only one message should be readable. Reply JSON: "
        '{"status":"pass|fail","reason":"<short>"}.\n\n'
        f"![thumb](data:image/png;base64,{thumbnail_b64})"
    )


def title_body_prompt(title: str, body: str) -> str:
    return (
        "The slide title makes one claim; the body must prove that claim "
        "and add nothing else. Judge whether the body proves the title.\n"
        'Reply JSON: {"status":"pass|fail","reason":"<short>"}.\n\n'
        f"TITLE: {title}\nBODY:\n{body}"
    )


def claim_title_prompt(title: str, body: str) -> str:
    return (
        "A claim title states a proposition that could be argued; a topic "
        "title only names the subject. Judge whether this title is a "
        "claim (pass) or a topic (fail).\n"
        'Reply JSON: {"status":"pass|fail","reason":"<short>"}.\n\n'
        f"TITLE: {title}\nBODY:\n{body}"
    )


def bullet_dump_prompt(title: str, body: str) -> str:
    return (
        "A slide should carry one idea per slide. If this slide reads as a "
        "list of >5 disconnected bullets or covers multiple ideas, fail.\n"
        'Reply JSON: {"status":"pass|fail","reason":"<short>"}.\n\n'
        f"TITLE: {title}\nBODY:\n{body}"
    )


def claim_evidence_prompt(
    title: str,
    body: str,
    *,
    target_claim: str | None = None,
) -> str:
    """Prompt for the mid-plan claim-evidence gate (step 2b).

    Asks two questions:
    1. Does the body provide evidence for the title's claim?
    2. Is there content in the body unrelated to the title?

    If *target_claim* is provided (from design_brief.slides[i].claim),
    it is shown as the intended claim so the LLM can flag title drift.

    Returns JSON:
        {
          "verdict": "clean" | "dirty",
          "rationale": "<one-line explanation>",
          "suggested_title": "<rewritten title>" | null,
          "suggested_body": "<hint to improve body>" | null
        }
    """
    claim_hint = (
        f"\nINTENDED CLAIM (from design brief): {target_claim}"
        if target_claim else ""
    )
    return (
        "You are reviewing a presentation slide plan (pre-render) for "
        "claim-evidence coherence.\n\n"
        "Answer two questions:\n"
        "1. Does the body provide direct evidence for the title's claim?\n"
        "2. Is there body content unrelated to the title's claim?\n\n"
        "Verdict: 'clean' if the body supports the claim and is focused; "
        "'dirty' if the body fails to support the title OR contains "
        "off-topic content.\n\n"
        "Reply ONLY with JSON (no markdown fences):\n"
        '{"verdict":"clean|dirty","rationale":"<one line>","suggested_title":'
        '"<rewritten title or null>","suggested_body":"<body improvement hint or null>"}\n'
        f"\nTITLE: {title}{claim_hint}\nBODY:\n{body}"
    )
