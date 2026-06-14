"""Deck-brief schema validator, defaults, and empty-brief factory."""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

_SCHEMA_PATH = Path(__file__).parent / "deck_brief.schema.json"

with _SCHEMA_PATH.open() as _fp:
    _SCHEMA = json.load(_fp)

_VALIDATOR = Draft202012Validator(_SCHEMA)

DEFAULTS: dict = {
    "schema_version": 1,
    "audience_prior": "some",
    "visual_style": "mixed",
    "length_hint": "standard",
    "tone": "brand-default",
    "must_include": [],
    "constraints": {},
}


def validate_brief(brief: dict) -> list[str]:
    """Return human-readable error strings. Empty list = valid."""
    return [
        f"{'/'.join(str(p) for p in err.absolute_path)}: {err.message}"
        if list(err.absolute_path)
        else err.message
        for err in sorted(_VALIDATOR.iter_errors(brief), key=lambda e: list(e.absolute_path))
    ]


def empty_brief() -> dict:
    """Return a brief with required fields as <<unset>> sentinels, optional fields absent."""
    return {
        "schema_version": 1,
        "goal": "<<unset>>",
        "audience": "<<unset>>",
        "deck_type": "<<unset>>",
    }
