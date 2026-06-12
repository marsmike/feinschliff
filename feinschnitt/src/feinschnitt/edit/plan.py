"""Authored edit-plan loading.

The authored plan is IMMUTABLE for the pipeline (design decision D2):
alignment writes a derived edit_plan.aligned.json into the workdir; nothing
ever rewrites the author's file.
"""
from __future__ import annotations

import json
from pathlib import Path

from feinschnitt.edit import EditError


def load_plan(path: Path) -> dict:
    if not path.exists():
        raise EditError(f"plan not found: {path}")
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise EditError(f"plan is not valid JSON: {path} ({exc})") from exc
    if not isinstance(data, dict) or not isinstance(data.get("beats"), list):
        raise EditError(f"plan must be an object with a 'beats' list: {path}")
    return data
