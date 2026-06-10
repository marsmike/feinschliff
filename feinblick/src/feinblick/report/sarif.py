"""SARIF 2.1.0 reporter — synthesized natively (no engine emits feinblick SARIF).

Shape: a single run whose tool driver is ``feinblick`` with a deduplicated
``rules[]`` table, and one ``results[]`` entry per finding carrying ruleId,
level (``severity.sarif_level``), a message, and a physical location.
"""
from __future__ import annotations

import json as _json

from feinblick.model import Finding

_SCHEMA = "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json"
_FALLBACK_RULE_ID = "feinblick:finding"


def _rule_id(f: Finding) -> str:
    return f.rule_id or _FALLBACK_RULE_ID


def _rules(findings: list[Finding]) -> list[dict]:
    """Unique rule descriptors, ordered by first appearance, sorted by id."""
    seen: dict[str, dict] = {}
    for f in findings:
        rid = _rule_id(f)
        if rid not in seen:
            seen[rid] = {
                "id": rid,
                "name": rid,
                "shortDescription": {"text": f.category.value},
            }
    return [seen[rid] for rid in sorted(seen)]


def _location(f: Finding) -> dict:
    physical: dict = {"artifactLocation": {"uri": f.location.path}}
    if f.location.line is not None:
        physical["region"] = {"startLine": f.location.line}
    return {"physicalLocation": physical}


def _result(f: Finding) -> dict:
    return {
        "ruleId": _rule_id(f),
        "level": f.severity.sarif_level,
        "message": {"text": f.message},
        "locations": [_location(f)],
    }


def render(findings: list[Finding], verdict: str, health: dict, meta: dict) -> str:
    doc = {
        "$schema": _SCHEMA,
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "feinblick",
                        "informationUri": "https://github.com/marsmike/feinschmiede",
                        "rules": _rules(findings),
                    }
                },
                "results": [_result(f) for f in findings],
            }
        ],
    }
    return _json.dumps(doc, indent=2, sort_keys=False)
