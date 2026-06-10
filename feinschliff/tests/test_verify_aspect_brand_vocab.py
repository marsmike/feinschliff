"""`deck verify-aspect brand` must validate fill tokens against the
canonical brand_bridge vocabulary (SEMANTIC_NAMES + the upstream
Excalidraw color aliases), not a hardcoded copy that drifts: the old
25-name copy warned on valid fills (chart-series-*, danger, status-on)
and green-lit raw token names that don't build (graphite, paper-2)."""
from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import yaml

from feinschmiede.diagrams.brand_bridge import SEMANTIC_NAMES
from feinschmiede.diagrams.excalidraw_expand import _COLOR_ALIASES
from feinschliff.cli.deck import cmd_verify_aspect

CANONICAL = SEMANTIC_NAMES | frozenset(_COLOR_ALIASES)


def _run_brand_aspect(diagram_dsl: str, tmp_path: Path) -> list[dict]:
    plan_file = tmp_path / "plan.yaml"
    plan_file.write_text(yaml.safe_dump({
        "brand": "feinschliff",
        "slides": [{"layout": "x.slide.dsl", "content": {"diagram_dsl": diagram_dsl}}],
    }))
    out_file = tmp_path / "brand.json"
    rc = cmd_verify_aspect(SimpleNamespace(
        aspect="brand", plan=str(plan_file), output=str(out_file),
        design_brief=None,
    ))
    assert rc == 0
    return json.loads(out_file.read_text(encoding="utf-8"))["findings"]


def test_vocabulary_equals_brand_bridge(tmp_path):
    """Every canonical name passes; only off-vocabulary names are flagged.

    Iterates the live SEMANTIC_NAMES / _COLOR_ALIASES so an engine-side
    vocabulary change propagates here without a test edit."""
    impostors = {"graphite", "paper-2", "severity-high", "status-done"}
    assert impostors.isdisjoint(CANONICAL)
    dsl = "\n".join(
        f'box b{i} 0,0 100x60 "x" fill:{name}'
        for i, name in enumerate(sorted(CANONICAL | impostors))
    )
    findings = _run_brand_aspect(dsl, tmp_path)
    flagged = {
        re.search(r"fill:([a-z0-9_-]+)", f["message"]).group(1)
        for f in findings
    }
    assert flagged == impostors


def test_previously_flagged_valid_tokens_pass(tmp_path):
    """Names the old hardcoded list rejected but brand_bridge resolves."""
    dsl = (
        'box b1 0,0 100x60 "a" fill:chart-series-1\n'
        'box b2 0,80 100x60 "b" fill:danger\n'
        'box b3 0,160 100x60 "c" fill:status-on\n'
        'box b4 0,240 100x60 "d" fill:start\n'
    )
    assert _run_brand_aspect(dsl, tmp_path) == []
