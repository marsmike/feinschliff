"""Design-brief validator. Loads the committed JSON schema and validates brief dicts."""
from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator

_SCHEMA_PATH = Path(__file__).parent / "design_brief.schema.json"

with _SCHEMA_PATH.open() as _fp:
    _SCHEMA = json.load(_fp)

_VALIDATOR = Draft202012Validator(_SCHEMA)


def validate_brief(brief: dict) -> list[str]:
    """Return a list of human-readable error strings. Empty list = valid."""
    return [
        f"{'/'.join(str(p) for p in err.absolute_path)}: {err.message}"
        for err in sorted(_VALIDATOR.iter_errors(brief), key=lambda e: list(e.absolute_path))
    ]


def load_brief(path: Path) -> dict:
    """Load and validate a brief from disk. Raises ValueError with details on invalid."""
    with path.open() as fp:
        brief = json.load(fp)
    errors = validate_brief(brief)
    if errors:
        raise ValueError(f"Invalid design brief {path}:\n" + "\n".join(f"  - {e}" for e in errors))
    return brief


def save_brief(brief: dict, path: Path) -> None:
    """Validate and write a brief to disk. Raises ValueError if invalid."""
    errors = validate_brief(brief)
    if errors:
        raise ValueError("Refusing to save invalid design brief:\n" + "\n".join(f"  - {e}" for e in errors))
    with path.open("w") as fp:
        json.dump(brief, fp, indent=2, ensure_ascii=False)
        fp.write("\n")
