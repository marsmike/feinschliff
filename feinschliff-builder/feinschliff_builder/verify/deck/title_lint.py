"""Shim — re-exports from feinschliff.verify.deck.title_lint.

The implementation moved to feinschliff core. This shim keeps old import
paths working. Will be removed in a follow-up release.
"""
from __future__ import annotations

from feinschliff.verify.deck.title_lint import *  # noqa: F401,F403
from feinschliff.verify.deck.title_lint import TitleLintIssue, lint_titles

__all__ = ["TitleLintIssue", "lint_titles"]
