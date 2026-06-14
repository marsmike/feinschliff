"""Arc-schema YAML loader and validator."""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

_SCHEMA_PATH = Path(__file__).parent / "arc.schema.json"
_ARCS_DIR = Path(__file__).parent / "arcs"

with _SCHEMA_PATH.open() as _fp:
    _SCHEMA = json.load(_fp)

_VALIDATOR = Draft202012Validator(_SCHEMA)


def validate_arc(schema_dict: dict) -> list[str]:
    """Validate a single arc schema dict; return error strings. Empty list = valid."""
    return [
        f"{'/'.join(str(p) for p in err.absolute_path)}: {err.message}"
        if list(err.absolute_path)
        else err.message
        for err in sorted(_VALIDATOR.iter_errors(schema_dict), key=lambda e: list(e.absolute_path))
    ]


def load_arc(path: Path) -> dict:
    """Load a YAML arc schema file, validate it, and return the dict.

    Raises ValueError if the file fails validation.
    """
    with path.open() as fp:
        data = yaml.safe_load(fp)
    errors = validate_arc(data)
    if errors:
        raise ValueError(f"Arc schema at {path} is invalid:\n" + "\n".join(f"  - {e}" for e in errors))
    return data


def load_all_arcs() -> dict[str, dict]:
    """Discover and load every *.yaml in the arcs/ directory.

    Returns a mapping of {deck_type: schema_dict}.
    Raises ValueError on duplicate deck_type or any validation failure.
    """
    result: dict[str, dict] = {}
    for yaml_path in sorted(_ARCS_DIR.glob("*.yaml")):
        arc = load_arc(yaml_path)
        deck_type = arc["deck_type"]
        if deck_type in result:
            raise ValueError(
                f"Duplicate deck_type '{deck_type}' found in {yaml_path} "
                f"(already loaded from another file)"
            )
        result[deck_type] = arc
    return result
