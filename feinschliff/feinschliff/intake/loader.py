"""Load and save deck_brief.yaml files."""
from __future__ import annotations

from pathlib import Path

import yaml

from .schema import validate_brief


def load_brief(path: Path) -> dict:
    """Load and validate a brief from a YAML file. Raises ValueError with details on invalid."""
    with path.open() as fp:
        brief = yaml.safe_load(fp)
    if not isinstance(brief, dict):
        raise ValueError(f"Expected a YAML mapping in {path}, got {type(brief).__name__}")
    errors = validate_brief(brief)
    if errors:
        raise ValueError(f"Invalid deck brief {path}:\n" + "\n".join(f"  - {e}" for e in errors))
    return brief


def save_brief(brief: dict, path: Path) -> None:
    """Validate and write a brief to a YAML file. Raises ValueError if invalid."""
    errors = validate_brief(brief)
    if errors:
        raise ValueError("Refusing to save invalid deck brief:\n" + "\n".join(f"  - {e}" for e in errors))
    with path.open("w") as fp:
        yaml.safe_dump(brief, fp, allow_unicode=True, sort_keys=False)
