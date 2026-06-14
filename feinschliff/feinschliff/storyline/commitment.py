"""Commitment-document loader, validator, and arc-alignment checker."""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

_SCHEMA_PATH = Path(__file__).parent / "commitment.schema.json"

with _SCHEMA_PATH.open() as _fp:
    _SCHEMA = json.load(_fp)

_VALIDATOR = Draft202012Validator(_SCHEMA)


def validate_commitment(c: dict) -> list[str]:
    """Return human-readable error strings. Empty list = valid."""
    return [
        f"{'/'.join(str(p) for p in err.absolute_path)}: {err.message}"
        if list(err.absolute_path)
        else err.message
        for err in sorted(_VALIDATOR.iter_errors(c), key=lambda e: list(e.absolute_path))
    ]


def load_commitment(path: Path) -> dict:
    """Load and validate a commitment YAML file.

    Raises ValueError if validation fails.
    """
    with path.open() as fp:
        data = yaml.safe_load(fp)
    errors = validate_commitment(data)
    if errors:
        raise ValueError(
            f"Commitment document at {path} is invalid:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )
    return data


def save_commitment(c: dict, path: Path) -> None:
    """Validate and write a commitment dict to a YAML file.

    Raises ValueError if validation fails before writing.
    """
    errors = validate_commitment(c)
    if errors:
        raise ValueError(
            "Cannot save invalid commitment document:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fp:
        yaml.safe_dump(c, fp, allow_unicode=True, sort_keys=False)


def check_arc_alignment(commitment: dict, arc: dict) -> list[str]:
    """Check that every required arc act has a matching key_move entry.

    The match is loose: a key_move matches an act if the lowercased text of
    the key_move contains at least one word from the act's name (split on '_').

    Returns a list of error strings. Empty list = all required acts covered.
    """
    errors: list[str] = []
    key_moves_text = " ".join(km.lower() for km in commitment.get("key_moves", []))
    for act in arc.get("acts", []):
        if not act.get("required", True):
            continue
        name: str = act["name"]
        search_terms = name.split("_")
        if not any(term in key_moves_text for term in search_terms):
            errors.append(
                f"required act '{name}' has no matching key_move "
                f"(search terms: {search_terms})"
            )
    return errors
