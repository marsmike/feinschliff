"""Regression: excalidraw-diagram-full fixture must not return to
'arrow hell'.

Before 2026-05-15 the fixture had 19 arrows including 6 cross-zone
arrows from the upper request-flow into the bottom Trust & Policy
band (gateway→iam, paysvc→kms, ordersvc→policy, paysvc→pii,
bus→audit, notify→dlq). Every cross-zone arrow becomes a long
diagonal that crosses other arrows — visually impenetrable.

The fix trimmed to the main request-flow path (12 arrows, matching
the "twelve hops" in the action_title) and dropped every cross-zone
arrow. The Trust & policy zone now reads as implicit context.

This test caps the fixture at ≤14 arrows so future contributors
don't reflexively wire every box-to-box dependency they think of.
"""
from __future__ import annotations

import re
from pathlib import Path


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "tests" / "fixtures" / "layouts" / "excalidraw-diagram-full.yaml"
)

# arrow lines inside diagram_dsl look like:  "  arrow client -> waf"
ARROW_RE = re.compile(r"^\s*arrow\s+\S+\s+->\s+\S+", re.MULTILINE)


def _arrow_count() -> int:
    return len(ARROW_RE.findall(FIXTURE.read_text()))


def test_excalidraw_diagram_full_arrows_capped():
    """Fixture must not exceed the 'visually parseable' arrow budget."""
    n = _arrow_count()
    assert n <= 14, (
        f"excalidraw-diagram-full fixture has {n} arrows — exceeds the "
        f"14-arrow cap that keeps the diagram readable. Cross-zone "
        f"arrows in particular tend to crisscross with others; prefer "
        f"showing the Trust & Policy zone as context (boxes, no arrows)."
    )
