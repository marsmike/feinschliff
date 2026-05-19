"""Tests for lib/verify/static.py — pre-render static geometry verify.

These tests use real layouts from feinschliff/layouts/ so the slot budgets
are pixel-accurate (same as production). Hand-crafted plan dicts exercise
the three main code paths: clean, slot-overflow, and empty-placeholder.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BRANDS_DIR = REPO_ROOT / "brands"
BRAND_DIR = REPO_ROOT / "brands" / "feinschliff"
LAYOUTS_DIR = REPO_ROOT / "layouts"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_plan(layout_rel: str, content: dict, brand: str = "feinschliff") -> dict:
    """Build a minimal plan dict with one slide, using a toolkit layout."""
    return {
        "brand": brand,
        "out": "deck.pptx",
        "slides": [
            {
                "layout": f"layouts/{layout_rel}",
                "content": content,
            }
        ],
    }


# ---------------------------------------------------------------------------
# Import guard — the module must exist before tests run
# ---------------------------------------------------------------------------

def test_static_verify_importable():
    """lib.verify.static must be importable and export static_verify."""
    from lib.verify.static import static_verify  # noqa: F401
    assert callable(static_verify)


def test_defect_kind_has_empty_placeholder():
    """DefectKind must carry EMPTY_PLACEHOLDER."""
    from lib.defects import DefectKind
    assert hasattr(DefectKind, "EMPTY_PLACEHOLDER")
    assert DefectKind.EMPTY_PLACEHOLDER.value == "empty-placeholder"


# ---------------------------------------------------------------------------
# Happy path — clean plan → no defects
# ---------------------------------------------------------------------------

def test_clean_plan_returns_no_defects():
    """A properly filled end.slide.dsl plan produces zero defects.

    We use the ``end`` layout because it has only simple (non-array) slots:
    pgmeta, title, footnote, footer_left, footer_right.  Filling all of them
    should yield zero defects.
    """
    from lib.verify.static import static_verify

    plan = _make_plan(
        "end.slide.dsl",
        {
            "pgmeta": "Q1 2026",
            "title": "Thank you",
            "footnote": "Acme Corp",
            "footer_left": "Acme Corp",
            "footer_right": "2026",
        },
    )
    defects = static_verify(plan, BRAND_DIR)
    assert defects == [], f"Expected no defects, got: {defects}"


# ---------------------------------------------------------------------------
# slot-overflow
# ---------------------------------------------------------------------------

def test_overflow_plan_returns_slot_overflow_defect():
    """A title that overflows its pixel budget produces a SLOT_OVERFLOW defect.

    Uses executive-summary where action_title has max_lines=1, max_chars=84.
    A 150-char title must produce a SLOT_OVERFLOW defect.
    """
    from lib.verify.static import static_verify
    from lib.defects import DefectKind

    # action_title budget: max_lines=1, chars_per_line=84.
    # A 150-char title will wrap to 2 lines → overflow.
    long_title = (
        "We must urgently restructure our go-to-market approach because "
        "enterprise revenue has declined for three consecutive quarters"
    )
    assert len(long_title) > 84, "test precondition: title must exceed char budget"

    plan = _make_plan(
        "executive-summary.slide.dsl",
        {
            "action_title": long_title,
            "footer_left": "Corp",
            "footer_right": "2026",
        },
    )
    defects = static_verify(plan, BRAND_DIR)
    overflow = [d for d in defects if d.kind == DefectKind.SLOT_OVERFLOW]
    assert len(overflow) >= 1, (
        f"Expected ≥1 SLOT_OVERFLOW defect for a very long title, got: {defects}"
    )
    assert overflow[0].slide_index == 1


# ---------------------------------------------------------------------------
# empty-placeholder
# ---------------------------------------------------------------------------

def test_empty_placeholder_plan_returns_defect():
    """A plan where a required slot is empty returns EMPTY_PLACEHOLDER.

    Uses end.slide.dsl: title is an interpolated slot.  Supplying an empty
    string triggers the EMPTY_PLACEHOLDER defect.
    """
    from lib.verify.static import static_verify
    from lib.defects import DefectKind

    plan = _make_plan(
        "end.slide.dsl",
        {
            "pgmeta": "Q1 2026",
            "title": "",              # empty → should fire
            "footnote": "Acme Corp",
            "footer_left": "Corp",
            "footer_right": "2026",
        },
    )
    defects = static_verify(plan, BRAND_DIR)
    ep = [d for d in defects if d.kind == DefectKind.EMPTY_PLACEHOLDER]
    assert len(ep) >= 1, (
        f"Expected ≥1 EMPTY_PLACEHOLDER defect for empty title, got: {defects}"
    )
    assert ep[0].slide_index == 1


def test_missing_slot_fires_empty_placeholder():
    """Completely absent required slot (not in content dict) also fires."""
    from lib.verify.static import static_verify
    from lib.defects import DefectKind

    # title not provided at all in end.slide.dsl
    plan = _make_plan(
        "end.slide.dsl",
        {
            "pgmeta": "Q1 2026",
            "footnote": "Acme Corp",
            "footer_left": "Corp",
            "footer_right": "2026",
        },
    )
    defects = static_verify(plan, BRAND_DIR)
    ep = [d for d in defects if d.kind == DefectKind.EMPTY_PLACEHOLDER]
    assert any(d.meta.get("slot") == "title" for d in ep), (
        f"Expected EMPTY_PLACEHOLDER for missing 'title', got: {ep}"
    )


# ---------------------------------------------------------------------------
# Combined: 1 overflow + 1 empty-placeholder → at least 2 defects
# ---------------------------------------------------------------------------

def test_combined_overflow_and_empty_placeholder():
    """Hand-crafted plan with one overflow AND one empty slot → both defect kinds.

    Uses executive-summary (real layout):
    - action_title with 150 chars overflows the max_chars=84 budget.
    - summary="" triggers EMPTY_PLACEHOLDER.
    """
    from lib.verify.static import static_verify
    from lib.defects import DefectKind

    long_title = (
        "Revenue declined for three consecutive quarters because enterprise "
        "churn accelerated faster than new logo acquisition could offset"
    )
    assert len(long_title) > 84, "test precondition: title must exceed char budget"

    plan = _make_plan(
        "executive-summary.slide.dsl",
        {
            "action_title": long_title,  # overflow
            "summary": "",               # empty-placeholder
            "footer_left": "Corp",
            "footer_right": "2026",
        },
    )
    defects = static_verify(plan, BRAND_DIR)

    kinds = {d.kind for d in defects}
    assert DefectKind.SLOT_OVERFLOW in kinds, (
        f"Missing SLOT_OVERFLOW in {defects}"
    )
    assert DefectKind.EMPTY_PLACEHOLDER in kinds, (
        f"Missing EMPTY_PLACEHOLDER in {defects}"
    )
    overflow_at_1 = [
        d for d in defects
        if d.kind == DefectKind.SLOT_OVERFLOW and d.slide_index == 1
    ]
    ep_at_1 = [
        d for d in defects
        if d.kind == DefectKind.EMPTY_PLACEHOLDER and d.slide_index == 1
    ]
    assert len(overflow_at_1) >= 1
    assert len(ep_at_1) >= 1


# ---------------------------------------------------------------------------
# Multi-slide plan — defects carry correct slide_index
# ---------------------------------------------------------------------------

def test_multi_slide_slide_index_is_correct():
    """slide_index in Defect must match the position in the plan.

    Slide 1 is clean; slide 2 has an empty title → EMPTY_PLACEHOLDER on
    slide 2 only.
    """
    from lib.verify.static import static_verify
    from lib.defects import DefectKind

    plan = {
        "brand": "feinschliff",
        "out": "deck.pptx",
        "slides": [
            {
                "layout": "layouts/end.slide.dsl",
                "content": {
                    "pgmeta": "Q1 2026",
                    "title": "Thank you",
                    "footnote": "Acme Corp",
                    "footer_left": "Corp",
                    "footer_right": "2026",
                },
            },
            {
                "layout": "layouts/end.slide.dsl",
                "content": {
                    "pgmeta": "Q1 2026",
                    "title": "",          # empty on slide 2
                    "footnote": "Acme Corp",
                    "footer_left": "Corp",
                    "footer_right": "2026",
                },
            },
        ],
    }
    defects = static_verify(plan, BRAND_DIR)
    ep = [d for d in defects if d.kind == DefectKind.EMPTY_PLACEHOLDER]
    assert any(d.slide_index == 2 for d in ep), (
        f"Expected EMPTY_PLACEHOLDER on slide 2, got: {ep}"
    )
    # Slide 1 must not produce an EMPTY_PLACEHOLDER
    ep_slide1 = [d for d in ep if d.slide_index == 1]
    assert ep_slide1 == [], f"Slide 1 should be clean, got: {ep_slide1}"


# ---------------------------------------------------------------------------
# Severity
# ---------------------------------------------------------------------------

def test_defects_are_warn_severity():
    """Static verify defects must be WARN, not FATAL."""
    from lib.verify.static import static_verify
    from lib.defects import Severity

    plan = _make_plan(
        "end.slide.dsl",
        {"title": "", "footer_left": "Corp", "footer_right": "2026"},
    )
    defects = static_verify(plan, BRAND_DIR)
    assert defects, "Expected at least one defect to check severity"
    for d in defects:
        assert d.severity == Severity.WARN, (
            f"Expected WARN, got {d.severity} for {d}"
        )


# ---------------------------------------------------------------------------
# CLI — verify-static command
# ---------------------------------------------------------------------------

def test_cli_verify_static_clean_exits_zero(tmp_path):
    """feinschliff deck verify-static on a clean plan exits 0."""
    import yaml

    plan = _make_plan(
        "end.slide.dsl",
        {
            "pgmeta": "Q1 2026",
            "title": "Thank you",
            "footnote": "Acme Corp",
            "footer_left": "Corp",
            "footer_right": "2026",
        },
    )
    plan_file = tmp_path / "plan.yaml"
    plan_file.write_text(yaml.safe_dump(plan), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "deck", "verify-static", str(plan_file)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Expected exit 0 for clean plan; got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_cli_verify_static_defects_exits_one(tmp_path):
    """feinschliff deck verify-static on a bad plan exits 1."""
    import yaml

    plan = _make_plan(
        "end.slide.dsl",
        {"title": "", "footer_left": "Corp", "footer_right": "2026"},
    )
    plan_file = tmp_path / "plan.yaml"
    plan_file.write_text(yaml.safe_dump(plan), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "cli.main", "deck", "verify-static", str(plan_file)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, (
        f"Expected exit 1 for defect plan; got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_cli_verify_static_json_output(tmp_path):
    """--json flag emits a JSON array of defect dicts."""
    import yaml

    plan = _make_plan(
        "end.slide.dsl",
        {"title": "", "footer_left": "Corp", "footer_right": "2026"},
    )
    plan_file = tmp_path / "plan.yaml"
    plan_file.write_text(yaml.safe_dump(plan), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable, "-m", "cli.main",
            "deck", "verify-static", str(plan_file), "--json",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "kind" in data[0]
    assert "slide_index" in data[0]


# ---------------------------------------------------------------------------
# plan_dir parameter — layout relative to plan file's directory
# ---------------------------------------------------------------------------

def test_plan_dir_resolves_layout_relative_to_plan_file(tmp_path):
    """static_verify(plan_dir=...) finds a layout copied next to the plan file.

    Copies end.slide.dsl into a temp directory alongside a plan.yaml that
    references it as ``layouts/end.slide.dsl``.  Without plan_dir the resolver
    falls back to REPO_ROOT (where the layout also exists, so that would still
    pass), but here we use a layout name that does NOT exist under REPO_ROOT to
    prove the plan_dir path is actually taken.
    """
    from lib.verify.static import static_verify

    # Create a subdirectory that mimics `layouts/` next to the plan
    layouts_dir = tmp_path / "layouts"
    layouts_dir.mkdir()
    src = LAYOUTS_DIR / "end.slide.dsl"
    dst = layouts_dir / "custom_end.slide.dsl"
    dst.write_bytes(src.read_bytes())

    plan = {
        "brand": "feinschliff",
        "out": "deck.pptx",
        "slides": [
            {
                "layout": "layouts/custom_end.slide.dsl",
                "content": {
                    "pgmeta": "Q1 2026",
                    "title": "Thank you",
                    "footnote": "Acme Corp",
                    "footer_left": "Corp",
                    "footer_right": "2026",
                },
            }
        ],
    }

    # Without plan_dir: layout not found under REPO_ROOT (name is custom_end)
    # → no defects but also no overflow checks (slide skipped silently).
    # With plan_dir=tmp_path: layout resolves → clean plan → no defects.
    defects = static_verify(plan, BRAND_DIR, plan_dir=tmp_path)
    assert defects == [], (
        f"Expected no defects when plan_dir resolves a custom layout; got: {defects}"
    )


# ---------------------------------------------------------------------------
# SLOT_OVERFLOW meta fields — budget_chars and over_by
# ---------------------------------------------------------------------------

def test_slot_overflow_meta_contains_budget_and_over_by():
    """SLOT_OVERFLOW defect meta must carry budget_chars and over_by.

    Task B1 (shorten_slot apply-fix) relies on these fields to compute the
    target character count for in-place trimming.
    """
    from lib.verify.static import static_verify
    from lib.defects import DefectKind

    long_title = (
        "We must urgently restructure our go-to-market approach because "
        "enterprise revenue has declined for three consecutive quarters"
    )
    assert len(long_title) > 84, "test precondition: title must exceed char budget"

    plan = _make_plan(
        "executive-summary.slide.dsl",
        {
            "action_title": long_title,
            "footer_left": "Corp",
            "footer_right": "2026",
        },
    )
    defects = static_verify(plan, BRAND_DIR)
    overflow = [d for d in defects if d.kind == DefectKind.SLOT_OVERFLOW]
    assert len(overflow) >= 1, f"Expected ≥1 SLOT_OVERFLOW defect; got: {defects}"

    d = overflow[0]
    assert "budget_chars" in d.meta, (
        f"SLOT_OVERFLOW meta must contain 'budget_chars'; got: {d.meta}"
    )
    assert "over_by" in d.meta, (
        f"SLOT_OVERFLOW meta must contain 'over_by'; got: {d.meta}"
    )
    assert isinstance(d.meta["budget_chars"], int), (
        f"budget_chars must be int; got {type(d.meta['budget_chars'])}"
    )
    assert isinstance(d.meta["over_by"], int), (
        f"over_by must be int; got {type(d.meta['over_by'])}"
    )
    assert d.meta["budget_chars"] > 0, "budget_chars must be positive"
    assert d.meta["over_by"] > 0, (
        f"over_by must be > 0 for an overflowing title; got {d.meta['over_by']}"
    )
    assert d.meta["over_by"] == max(0, len(long_title) - d.meta["budget_chars"]), (
        "over_by must equal max(0, len(value) - budget_chars)"
    )


# ---------------------------------------------------------------------------
# deck build --strict-static integration
# ---------------------------------------------------------------------------

def test_deck_build_strict_static_exits_nonzero_on_bad_plan(tmp_path):
    """deck build --strict-static aborts before render when defects exist."""
    import yaml

    plan = _make_plan(
        "end.slide.dsl",
        {"title": "", "footer_left": "Corp", "footer_right": "2026"},
    )
    plan_file = tmp_path / "plan.yaml"
    plan_file.write_text(yaml.safe_dump(plan), encoding="utf-8")
    out_pptx = tmp_path / "out.pptx"

    result = subprocess.run(
        [
            sys.executable, "-m", "cli.main",
            "deck", "build", str(plan_file),
            "-o", str(out_pptx),
            "--strict-static",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0, (
        f"Expected non-zero exit for --strict-static with defects; "
        f"got {result.returncode}\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    # The .pptx must NOT have been written (aborted before render).
    assert not out_pptx.exists(), (
        "deck.pptx should NOT be written when --strict-static aborts early"
    )
