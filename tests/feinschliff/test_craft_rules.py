"""Tests for feinschliff.quality.craft_rules — one positive + one negative per rule."""
from __future__ import annotations

from feinschliff.quality import (
    check_craft_rules,
    write_craft_report,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slide(layout: str, **content) -> dict:
    return {"layout": layout, "content_inline": content}


def _slide_bar(**content) -> dict:
    return _slide("/layouts/bar-chart.slide.dsl", **content)


# ---------------------------------------------------------------------------
# no-pie-chart
# ---------------------------------------------------------------------------

def test_no_pie_chart_fails():
    slides = [_slide("/layouts/pie-chart.slide.dsl", title="Revenue breakdown")]
    report = check_craft_rules(slides)
    rules = [i.rule for i in report.issues]
    assert "no-pie-chart" in rules
    assert any(i.severity == "fail" for i in report.issues if i.rule == "no-pie-chart")
    assert report.verdict == "fail"


def test_no_pie_chart_passes_otherwise():
    slides = [_slide_bar(title="Revenue grows 12% YoY")]
    report = check_craft_rules(slides)
    assert all(i.rule != "no-pie-chart" for i in report.issues)


# ---------------------------------------------------------------------------
# no-3d-chart
# ---------------------------------------------------------------------------

def test_no_3d_chart_fails():
    slides = [_slide("/layouts/bar-chart-3d.slide.dsl", title="Sales volumes")]
    report = check_craft_rules(slides)
    assert any(i.rule == "no-3d-chart" and i.severity == "fail" for i in report.issues)


def test_no_3d_chart_passes_flat():
    slides = [_slide_bar(title="Sales volumes grew")]
    report = check_craft_rules(slides)
    assert all(i.rule != "no-3d-chart" for i in report.issues)


# ---------------------------------------------------------------------------
# title-word-count
# ---------------------------------------------------------------------------

def test_title_too_long_fails_at_21_words():
    long_title = " ".join([f"word{n}" for n in range(21)])
    slides = [_slide_bar(title=long_title)]
    report = check_craft_rules(slides)
    issues = [i for i in report.issues if i.rule == "title-word-count"]
    assert issues
    assert issues[0].severity == "fail"
    assert report.verdict == "fail"


def test_title_too_long_warns_at_16_words():
    warn_title = " ".join([f"word{n}" for n in range(16)])
    slides = [_slide_bar(title=warn_title)]
    report = check_craft_rules(slides)
    issues = [i for i in report.issues if i.rule == "title-word-count"]
    assert issues
    assert issues[0].severity == "warn"


def test_title_word_count_clean_at_15():
    short_title = " ".join([f"word{n}" for n in range(15)])
    slides = [_slide_bar(title=short_title)]
    report = check_craft_rules(slides)
    assert all(i.rule != "title-word-count" for i in report.issues)


# ---------------------------------------------------------------------------
# body-word-count
# ---------------------------------------------------------------------------

def test_body_word_count_warns():
    body_60 = " ".join([f"word{n}" for n in range(60)])
    slides = [_slide("/layouts/text.slide.dsl", title="Revenue grows", body=body_60)]
    report = check_craft_rules(slides)
    issues = [i for i in report.issues if i.rule == "body-word-count"]
    assert issues
    assert issues[0].severity == "warn"


def test_body_word_count_fails_above_80():
    body_81 = " ".join([f"word{n}" for n in range(81)])
    slides = [_slide("/layouts/text.slide.dsl", title="Revenue grows", body=body_81)]
    report = check_craft_rules(slides)
    issues = [i for i in report.issues if i.rule == "body-word-count"]
    assert issues
    assert issues[0].severity == "fail"


# ---------------------------------------------------------------------------
# chart-title-claim
# ---------------------------------------------------------------------------

def test_chart_title_must_be_claim():
    # "Revenue Bar Chart" — a topic label, no finite verb
    slides = [_slide_bar(title="Revenue Bar Chart")]
    report = check_craft_rules(slides)
    issues = [i for i in report.issues if i.rule == "chart-title-claim"]
    assert issues
    assert issues[0].severity == "warn"


def test_chart_title_claim_passes():
    # "Revenue grows 12% YoY" — contains the finite verb "grows"
    slides = [_slide_bar(title="Revenue grows 12% YoY")]
    report = check_craft_rules(slides)
    assert all(i.rule != "chart-title-claim" for i in report.issues)


# ---------------------------------------------------------------------------
# too-many-colors
# ---------------------------------------------------------------------------

def test_too_many_colors_warns():
    # 5 distinct token references in content
    content_text = (
        "$primary $secondary $accent $neutral $highlight some text"
    )
    slides = [_slide("/layouts/text.slide.dsl", title="Revenue grows", body=content_text)]
    report = check_craft_rules(slides, brand_palette=[])
    issues = [i for i in report.issues if i.rule == "too-many-colors"]
    assert issues
    assert issues[0].severity == "warn"


def test_too_many_colors_passes_at_four():
    content_text = "$primary $secondary $accent $neutral some text"
    slides = [_slide("/layouts/text.slide.dsl", title="Revenue grows", body=content_text)]
    report = check_craft_rules(slides, brand_palette=[])
    assert all(i.rule != "too-many-colors" for i in report.issues)


def test_too_many_colors_skipped_when_palette_none():
    # brand_palette=None → rule is not run at all
    content_text = "$primary $secondary $accent $neutral $highlight $extra text"
    slides = [_slide("/layouts/text.slide.dsl", title="Revenue grows", body=content_text)]
    report = check_craft_rules(slides, brand_palette=None)
    assert all(i.rule != "too-many-colors" for i in report.issues)


# ---------------------------------------------------------------------------
# clean slide
# ---------------------------------------------------------------------------

def test_clean_slide_returns_clean_verdict():
    # 5-word title with a verb, no chart layout, modest body
    slides = [_slide(
        "/layouts/text.slide.dsl",
        title="Revenue grows this quarter",
        body="A short body sentence here.",
    )]
    report = check_craft_rules(slides)
    assert report.verdict == "clean"
    assert report.issues == []


# ---------------------------------------------------------------------------
# write_craft_report
# ---------------------------------------------------------------------------

def test_write_report(tmp_path):
    slides = [_slide("/layouts/pie-chart.slide.dsl", title="Revenue breakdown")]
    report = check_craft_rules(slides)
    out = tmp_path / "craft_report.md"
    write_craft_report(report, out)
    text = out.read_text()
    assert "no-pie-chart" in text
    assert "Verdict" in text
    assert "fail" in text
