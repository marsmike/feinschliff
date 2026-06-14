"""Merge two partial deck briefs; answers always win."""
from __future__ import annotations

from .schema import validate_brief


def merge_with_answers(base: dict, answers: dict) -> dict:
    """Shallow-merge base and answers (answers wins), deep-merge constraints, validate result."""
    result = dict(base)
    for key, value in answers.items():
        if key == "constraints" and isinstance(result.get("constraints"), dict) and isinstance(value, dict):
            merged_constraints = dict(result["constraints"])
            merged_constraints.update(value)
            result["constraints"] = merged_constraints
        else:
            result[key] = value

    errors = validate_brief(result)
    if errors:
        raise ValueError("Merged brief is invalid:\n" + "\n".join(f"  - {e}" for e in errors))
    return result
