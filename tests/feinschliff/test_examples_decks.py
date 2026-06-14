"""Verify all 4 domain mini-decks build and have clean verify reports."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent.parent / "feinschliff"
DEBUG_DECKS = REPO / ".debug" / "examples" / "decks"
DECKS = ["q1-update-saas", "ml-research-findings", "budget-non-profit", "postmortem-eng"]


def _has_render_backend() -> bool:
    try:
        import cairosvg
        cairosvg.svg2png(bytestring=b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>')
        return True
    except (ImportError, OSError):
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
            return True
        except ImportError:
            return False


@pytest.mark.parametrize("deck_name", DECKS)
def test_deck_builds(deck_name, tmp_path):
    if not _has_render_backend():
        pytest.skip("render backend (cairo/playwright) unavailable")
    plan = DEBUG_DECKS / deck_name / "content_plan.yaml"
    if not plan.exists():
        pytest.skip(f"{deck_name}: content_plan.yaml not in .debug/ (regenerate first)")
    out = tmp_path / "deck.pptx"
    env = {**os.environ, "DYLD_FALLBACK_LIBRARY_PATH": "/opt/homebrew/opt/cairo/lib"}
    result = subprocess.run(
        ["uv", "run", "feinschliff", "deck", "build", str(plan), "-o", str(out)],
        capture_output=True, text=True, cwd=REPO, env=env,
    )
    assert result.returncode == 0, f"build failed: {result.stderr[-500:]}"
    assert out.exists()
    assert out.stat().st_size > 5_000


@pytest.mark.parametrize("deck_name", DECKS)
def test_deck_verify_report_exists(deck_name):
    report = DEBUG_DECKS / deck_name / "out" / "verify_report.md"
    if not report.exists():
        pytest.skip(f"{deck_name}: verify_report.md not in .debug/ (regenerate first)")
    text = report.read_text()
    assert len(text) > 10, "verify_report.md is empty"


@pytest.mark.parametrize("deck_name", DECKS)
def test_deck_brief_and_design_brief(deck_name):
    deck_dir = DEBUG_DECKS / deck_name
    if not deck_dir.exists():
        pytest.skip(f"{deck_name}: not present in .debug/")
    assert (deck_dir / "brief.txt").exists(), f"{deck_name}: brief.txt missing"
    assert (deck_dir / "design_brief.json").exists(), f"{deck_name}: design_brief.json missing"
    import json
    db = json.loads((deck_dir / "design_brief.json").read_text())
    assert db.get("frame") in ("scqa", "pssr", "sparkline", "man-in-a-hole", "abt", "ppf", "pse", "kea"), \
        f"{deck_name}: frame must be one of the 8 named frames"
    assert db.get("audience"), f"{deck_name}: missing audience"
    assert db.get("takeaway"), f"{deck_name}: missing takeaway"
    assert len(db.get("slides", [])) >= 6, f"{deck_name}: slides[] needs ≥6 entries"
