"""Core LLM judge helper — minimal rubric caller for deck quality gates.

This module provides only `_judge`, the low-level Anthropic API call used
by ghost_deck and claim_evidence. The full rubric suite (squint, title-body,
claim-title, bullet-dump with caching) lives in feinschliff-builder, which
has access to the render artefacts those rubrics need.
"""
from __future__ import annotations

import functools
import json
import os
import re
from typing import Any


@functools.lru_cache(maxsize=1)
def _client():
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise SystemExit(
            "verify: anthropic library not installed; "
            "install it with `uv pip install anthropic` or use --offline to skip LLM calls"
        ) from exc
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit(
            "verify: ANTHROPIC_API_KEY not set; use --offline to skip LLM calls"
        )
    return Anthropic(api_key=api_key)


def _judge(prompt: str, model: str = "claude-haiku-4-5-20251001") -> dict[str, Any]:
    msg = _client().messages.create(
        model=model,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in msg.content if hasattr(b, "text")).strip()
    text = re.sub(r"^\s*```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?\s*```\s*$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"status": "fail", "reason": f"unparseable: {text[:200]}"}
