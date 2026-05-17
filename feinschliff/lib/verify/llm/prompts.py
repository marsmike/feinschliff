"""Prompt templates for LLM defect classes."""
from __future__ import annotations

from pathlib import Path

REFS = Path(__file__).resolve().parents[3] / "skills" / "deck" / "references"


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
