"""Deck brief intake — load, validate, infer, merge."""
from __future__ import annotations

from .infer import infer_from_text
from .loader import load_brief, save_brief
from .merge import merge_with_answers
from .schema import DEFAULTS, empty_brief, validate_brief

__all__ = [
    "load_brief",
    "save_brief",
    "validate_brief",
    "infer_from_text",
    "merge_with_answers",
    "empty_brief",
    "DEFAULTS",
]
