"""Shim — re-exports from feinschliff.verify.deck.claim_evidence.

The implementation moved to feinschliff core. This shim keeps old import
paths working. Will be removed in a follow-up release.
"""
from __future__ import annotations

from feinschliff.verify.deck.claim_evidence import *  # noqa: F401,F403
from feinschliff.verify.deck.claim_evidence import (
    ClaimEvidenceResult,
    judge_plan,
    write_report,
    _extract_slide_text,  # noqa: F401  private — exposed for backward-compat test patches
    _has_claim_role,       # noqa: F401  private — exposed for backward-compat test patches
    _judge,                # noqa: F401  private — exposed for backward-compat test patches
)

__all__ = ["ClaimEvidenceResult", "judge_plan", "write_report"]
