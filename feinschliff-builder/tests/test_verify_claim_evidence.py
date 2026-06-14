"""Tests for lib/verify/deck/claim_evidence.py — mid-plan claim-evidence gate.

TDD: written before implementation.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch


REPO = Path(__file__).resolve().parents[2]
FEINSCHLIFF = REPO / "feinschliff"


# ---------------------------------------------------------------------------
# Fixtures — minimal plan dicts
# ---------------------------------------------------------------------------

def _make_claim_slide(
    title: str = "Cloud migration saves 40% on infra",
    body: str = "AWS cost audit shows 38% reduction; one-time migration cost is $200k.",
    role: str = "evidence",
    index: int = 0,
) -> dict:
    return {
        "layout": "layouts/title-body.slide.dsl",
        "content": {"title": title, "body": body},
        "_meta": {"role": role},
    }


def _make_non_claim_slide(layout: str = "layouts/chapter-opener.slide.dsl") -> dict:
    return {
        "layout": layout,
        "content": {"title": "Chapter 1"},
        "_meta": {"role": "chapter"},
    }


def _make_plan(*slides) -> dict:
    return {"slides": list(slides)}


# ---------------------------------------------------------------------------
# Unit: extract_slide_text_from_plan
# ---------------------------------------------------------------------------

def test_extract_title_and_body_inline():
    from feinschliff.verify.deck.claim_evidence import _extract_slide_text

    slide = {
        "layout": "layouts/title-body.slide.dsl",
        "content": {"title": "Our costs are rising", "body": "Opex up 22% YoY."},
    }
    title, body = _extract_slide_text(slide)
    assert title == "Our costs are rising"
    assert "22%" in body


def test_extract_body_from_bullets():
    from feinschliff.verify.deck.claim_evidence import _extract_slide_text

    slide = {
        "layout": "layouts/bullets.slide.dsl",
        "content": {"title": "Three drivers", "bullets": ["Cost", "Speed", "Scale"]},
    }
    title, body = _extract_slide_text(slide)
    assert title == "Three drivers"
    assert "Cost" in body
    assert "Speed" in body


def test_extract_body_from_supporting_body():
    from feinschliff.verify.deck.claim_evidence import _extract_slide_text

    slide = {
        "content": {"title": "T", "body": "main body", "supporting_body": "secondary"},
    }
    title, body = _extract_slide_text(slide)
    assert "main body" in body
    assert "secondary" in body


def test_extract_gracefully_missing_slots():
    from feinschliff.verify.deck.claim_evidence import _extract_slide_text

    slide = {"content": {"subtitle": "Subtitle only"}}
    title, body = _extract_slide_text(slide)
    assert title == ""
    assert "Subtitle only" in body


# ---------------------------------------------------------------------------
# Unit: role classification
# ---------------------------------------------------------------------------

def test_claim_role_from_meta():
    from feinschliff.verify.deck.claim_evidence import _has_claim_role

    slide = {"_meta": {"role": "evidence"}}
    assert _has_claim_role(slide, brief_slide=None) is True


def test_non_claim_role_from_meta():
    from feinschliff.verify.deck.claim_evidence import _has_claim_role

    for role in ("chapter", "agenda", "closer", "end", "title", "cover", "divider", "quote"):
        slide = {"_meta": {"role": role}}
        assert _has_claim_role(slide, brief_slide=None) is False, f"should skip role={role}"


def test_claim_role_from_design_brief():
    from feinschliff.verify.deck.claim_evidence import _has_claim_role

    slide = {}  # no _meta.role
    brief_slide = {"role": "recommendation"}
    assert _has_claim_role(slide, brief_slide=brief_slide) is True


def test_non_claim_role_from_design_brief_overrides():
    from feinschliff.verify.deck.claim_evidence import _has_claim_role

    # design_brief says chapter → skip
    slide = {}
    brief_slide = {"role": "chapter"}
    assert _has_claim_role(slide, brief_slide=None) is True  # no role → default judge
    assert _has_claim_role(slide, brief_slide=brief_slide) is False


def test_no_role_defaults_to_claim():
    from feinschliff.verify.deck.claim_evidence import _has_claim_role

    slide = {}
    assert _has_claim_role(slide, brief_slide=None) is True


# ---------------------------------------------------------------------------
# Unit: judge_plan — offline mode
# ---------------------------------------------------------------------------

def test_judge_plan_offline_returns_clean_verdicts():
    from feinschliff.verify.deck.claim_evidence import judge_plan

    plan = _make_plan(
        _make_claim_slide(role="evidence"),
        _make_claim_slide(role="recommendation"),
    )
    results = judge_plan(plan, offline=True)
    assert len(results) == 2
    for r in results:
        assert r.verdict == "clean"
        assert "offline" in r.rationale.lower()
        assert r.suggested_title is None
        assert r.suggested_body is None


def test_judge_plan_offline_skips_non_claim_slides():
    from feinschliff.verify.deck.claim_evidence import judge_plan

    plan = _make_plan(
        _make_claim_slide(role="evidence"),
        _make_non_claim_slide(),  # chapter — should be skipped
        _make_claim_slide(role="result"),
    )
    results = judge_plan(plan, offline=True)
    assert len(results) == 2
    assert all(r.verdict == "clean" for r in results)


def test_judge_plan_offline_all_non_claim_returns_empty():
    from feinschliff.verify.deck.claim_evidence import judge_plan

    plan = _make_plan(
        _make_non_claim_slide(),
        {"_meta": {"role": "agenda"}, "content": {}},
        {"_meta": {"role": "closer"}, "content": {}},
    )
    results = judge_plan(plan, offline=True)
    assert results == []


def test_judge_plan_result_slide_indices_correct():
    from feinschliff.verify.deck.claim_evidence import judge_plan

    # slides: 0=chapter(skip), 1=evidence(judge), 2=chapter(skip), 3=result(judge)
    plan = _make_plan(
        _make_non_claim_slide(),
        _make_claim_slide(role="evidence"),
        _make_non_claim_slide(),
        _make_claim_slide(role="result"),
    )
    results = judge_plan(plan, offline=True)
    assert len(results) == 2
    assert results[0].slide_index == 2   # 1-based: slide at position 1 → index 2
    assert results[1].slide_index == 4


def test_judge_plan_with_design_brief_skips_by_brief_role():
    from feinschliff.verify.deck.claim_evidence import judge_plan

    plan = _make_plan(
        # plan says evidence role, but brief says chapter → brief wins
        {"_meta": {"role": "evidence"}, "content": {"title": "T", "body": "B"}},
    )
    brief = {"slides": [{"role": "chapter"}]}
    results = judge_plan(plan, design_brief=brief, offline=True)
    assert results == []


# ---------------------------------------------------------------------------
# Unit: judge_plan — with mocked _judge (online path)
# ---------------------------------------------------------------------------

def test_judge_plan_calls_judge_once_per_claim_slide(tmp_path: Path):
    from feinschliff.verify.deck import claim_evidence as ce_mod

    plan = _make_plan(
        _make_claim_slide(role="evidence"),
        _make_non_claim_slide(),
        _make_claim_slide(role="recommendation"),
    )

    mock_response = {
        "verdict": "clean",
        "rationale": "body supports the title claim",
        "suggested_title": None,
        "suggested_body": None,
    }

    with patch.object(ce_mod, "_judge", return_value=mock_response) as mock:
        results = ce_mod.judge_plan(plan, offline=False)

    assert mock.call_count == 2
    assert len(results) == 2
    assert all(r.verdict == "clean" for r in results)


def test_judge_plan_dirty_verdict_from_judge(tmp_path: Path):
    from feinschliff.verify.deck import claim_evidence as ce_mod

    plan = _make_plan(_make_claim_slide(role="evidence"))

    mock_response = {
        "verdict": "dirty",
        "rationale": "body talks about costs, title claims speed improvements",
        "suggested_title": "Costs rose 20% last quarter",
        "suggested_body": None,
    }

    with patch.object(ce_mod, "_judge", return_value=mock_response):
        results = ce_mod.judge_plan(plan, offline=False)

    assert len(results) == 1
    r = results[0]
    assert r.verdict == "dirty"
    assert "costs" in r.rationale.lower()
    assert r.suggested_title == "Costs rose 20% last quarter"
    assert r.suggested_body is None


def test_judge_plan_error_sentinel_yields_dirty(tmp_path: Path):
    """When _judge returns an error-sentinel (status=fail, no verdict key),
    the result must be dirty with the parse error surfaced in rationale."""
    from feinschliff.verify.deck import claim_evidence as ce_mod

    plan = _make_plan(_make_claim_slide(role="evidence"))

    error_sentinel = {"status": "fail", "reason": "unparseable: expecting value: line 1 column 1 (char 0)"}

    with patch.object(ce_mod, "_judge", return_value=error_sentinel):
        results = ce_mod.judge_plan(plan, offline=False)

    assert len(results) == 1
    r = results[0]
    assert r.verdict == "dirty"
    assert r.rationale.startswith("[judgment error]")
    assert "unparseable" in r.rationale


# ---------------------------------------------------------------------------
# Unit: write_report
# ---------------------------------------------------------------------------

def test_write_report_clean(tmp_path: Path):
    from feinschliff.verify.deck.claim_evidence import ClaimEvidenceResult, write_report

    results = [
        ClaimEvidenceResult(1, "clean", "body supports claim", None, None),
        ClaimEvidenceResult(3, "clean", "evidence present", None, None),
    ]
    out = tmp_path / "claim_evidence_report.md"
    verdict = write_report(out, results, slide_count=4)

    assert verdict == "clean"
    body = out.read_text()
    assert "Verdict: clean" in body
    assert "Slides judged: 2" in body
    assert "Slides total: 4" in body


def test_write_report_dirty(tmp_path: Path):
    from feinschliff.verify.deck.claim_evidence import ClaimEvidenceResult, write_report

    results = [
        ClaimEvidenceResult(1, "clean", "fine", None, None),
        ClaimEvidenceResult(2, "dirty", "body off-topic", "Better title", "Add evidence"),
    ]
    out = tmp_path / "claim_evidence_report.md"
    verdict = write_report(out, results, slide_count=3)

    assert verdict == "dirty"
    body = out.read_text()
    assert "Verdict: dirty" in body
    assert "Better title" in body
    assert "Add evidence" in body


def test_write_report_no_results(tmp_path: Path):
    from feinschliff.verify.deck.claim_evidence import write_report

    out = tmp_path / "claim_evidence_report.md"
    verdict = write_report(out, [], slide_count=3)
    assert verdict == "clean"
    body = out.read_text()
    assert "Verdict: clean" in body


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------

def _write_yaml_plan(tmp_path: Path, slides: list[dict]) -> Path:
    import yaml
    p = tmp_path / "plan.yaml"
    p.write_text(yaml.dump({"slides": slides}))
    return p


def _write_design_brief(tmp_path: Path, slides: list[dict]) -> Path:
    p = tmp_path / "design_brief.json"
    p.write_text(json.dumps({"slides": slides}))
    return p


def test_cli_clean_plan_exits_0(tmp_path: Path):
    """A plan where all claim slides are well-matched → exit 0."""
    plan = _write_yaml_plan(tmp_path, [
        {
            "layout": "layouts/title-body.slide.dsl",
            "content": {"title": "Revenue rose 18% in Q3", "body": "Q3 revenue was $4.2M vs $3.6M in Q2."},
            "_meta": {"role": "evidence"},
        },
    ])
    out = tmp_path / "claim_evidence_report.md"
    result = subprocess.run(
        [
            sys.executable, "-m", "feinschliff.cli", "deck", "claim-evidence",
            str(plan),
            "-o", str(out),
            "--offline",
        ],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )
    assert result.returncode == 0, result.stderr
    assert out.exists()
    assert "Verdict: clean" in out.read_text()


def test_cli_offline_non_claim_only_exits_0(tmp_path: Path):
    """A plan with only non-claim slides (all skipped) → exit 0."""
    plan = _write_yaml_plan(tmp_path, [
        {"content": {"title": "Chapter 1"}, "_meta": {"role": "chapter"}},
        {"content": {"title": "Agenda"}, "_meta": {"role": "agenda"}},
    ])
    out = tmp_path / "claim_evidence_report.md"
    result = subprocess.run(
        [sys.executable, "-m", "feinschliff.cli", "deck", "claim-evidence",
         str(plan), "-o", str(out), "--offline"],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )
    assert result.returncode == 0, result.stderr


def test_cmd_claim_evidence_dirty_exits_1(tmp_path: Path, monkeypatch):
    """cmd_claim_evidence returns exit code 1 when judge_plan yields a dirty result."""
    import argparse
    import yaml
    from feinschliff.verify.deck.claim_evidence import ClaimEvidenceResult
    import feinschliff.cli.deck as deck_cli

    plan_path = tmp_path / "plan.yaml"
    plan_path.write_text(yaml.dump({"slides": [
        {
            "layout": "layouts/title-body.slide.dsl",
            "content": {"title": "Costs cut by 50%", "body": "We just assumed it."},
            "_meta": {"role": "evidence"},
        }
    ]}))
    out_path = tmp_path / "report.md"

    def fake_judge_plan(*a, **kw):
        return [ClaimEvidenceResult(
            slide_index=1,
            verdict="dirty",
            rationale="body does not support the claim",
            suggested_title=None,
            suggested_body=None,
        )]

    monkeypatch.setattr(deck_cli, "judge_plan", fake_judge_plan)

    args = argparse.Namespace(
        plan=str(plan_path),
        design_brief=None,
        output=str(out_path),
        offline=True,
        model="claude-haiku-4-5-20251001",
    )
    exit_code = deck_cli.cmd_claim_evidence(args)
    assert exit_code == 1


def test_cli_missing_plan_exits_2(tmp_path: Path):
    out = tmp_path / "claim_evidence_report.md"
    result = subprocess.run(
        [sys.executable, "-m", "feinschliff.cli", "deck", "claim-evidence",
         str(tmp_path / "no_such_plan.yaml"),
         "-o", str(out),
         "--offline"],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )
    assert result.returncode == 2, result.stderr


def test_cli_with_design_brief(tmp_path: Path):
    plan = _write_yaml_plan(tmp_path, [
        {
            "layout": "layouts/title-body.slide.dsl",
            "content": {"title": "We shipped feature X", "body": "Beta launched March 3."},
        },
    ])
    brief = _write_design_brief(tmp_path, [{"role": "result"}])
    out = tmp_path / "claim_evidence_report.md"
    result = subprocess.run(
        [sys.executable, "-m", "feinschliff.cli", "deck", "claim-evidence",
         str(plan),
         "--design-brief", str(brief),
         "-o", str(out),
         "--offline"],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )
    assert result.returncode == 0, result.stderr


def test_cli_stderr_token_estimate(tmp_path: Path):
    """CLI should print a token-cost estimate line to stderr."""
    plan = _write_yaml_plan(tmp_path, [
        {
            "content": {"title": "Q3 margins expanded", "body": "Gross margin up 3pp."},
            "_meta": {"role": "evidence"},
        },
    ])
    out = tmp_path / "claim_evidence_report.md"
    result = subprocess.run(
        [sys.executable, "-m", "feinschliff.cli", "deck", "claim-evidence",
         str(plan), "-o", str(out), "--offline"],
        capture_output=True, text=True, cwd=FEINSCHLIFF,
    )
    assert result.returncode == 0, result.stderr
    # stderr should mention "slides judged" and "tokens"
    combined = (result.stderr + result.stdout).lower()
    assert "judged" in combined
    assert "token" in combined
