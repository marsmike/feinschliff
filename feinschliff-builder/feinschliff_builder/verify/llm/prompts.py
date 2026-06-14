"""Shim — re-exports from feinschliff.verify.llm.prompts.

The implementation moved to feinschliff core. This shim keeps old import
paths working. Will be removed in a follow-up release.
"""
from __future__ import annotations

from feinschliff.verify.llm.prompts import *  # noqa: F401,F403
from feinschliff.verify.llm.prompts import (
    squint_prompt,
    title_body_prompt,
    claim_title_prompt,
    bullet_dump_prompt,
    claim_evidence_prompt,
)

__all__ = [
    "squint_prompt",
    "title_body_prompt",
    "claim_title_prompt",
    "bullet_dump_prompt",
    "claim_evidence_prompt",
]
