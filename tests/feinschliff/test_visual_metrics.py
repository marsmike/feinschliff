from __future__ import annotations

import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from feinschliff.quality import compute_visual_metrics, VisualMetricsResult
from feinschliff.quality.visual_metrics_report import write_visual_metrics_report


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_white(w: int = 200, h: int = 150) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img = Image.new("RGB", (w, h), (255, 255, 255))
    img.save(tmp.name)
    return Path(tmp.name)


def _make_black(w: int = 200, h: int = 150) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img = Image.new("RGB", (w, h), (0, 0, 0))
    img.save(tmp.name)
    return Path(tmp.name)


def _make_centered_block(w: int = 200, h: int = 150) -> Path:
    """Small dark block centred on a white background — balanced."""
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    bx0, by0 = w // 2 - 20, h // 2 - 20
    bx1, by1 = w // 2 + 20, h // 2 + 20
    draw.rectangle([bx0, by0, bx1, by1], fill=(50, 50, 50))
    img.save(tmp.name)
    return Path(tmp.name)


def _make_bottom_right_block(w: int = 200, h: int = 150) -> Path:
    """Large dark block in bottom-right quadrant — unbalanced."""
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([w * 3 // 4, h * 3 // 4, w - 1, h - 1], fill=(10, 10, 10))
    img.save(tmp.name)
    return Path(tmp.name)


def _make_sparse_rects(w: int = 240, h: int = 160) -> Path:
    """A few well-separated rectangles — low collision."""
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Two rectangles with wide gaps between them
    draw.rectangle([10, 10, 40, 40], fill=(30, 30, 30))
    draw.rectangle([180, 110, 220, 140], fill=(30, 30, 30))
    img.save(tmp.name)
    return Path(tmp.name)


def _make_dense_rects(w: int = 240, h: int = 160) -> Path:
    """Tightly packed rectangles filling most of the image — many dense cells."""
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Fill most of the image with close rectangles
    for row in range(8):
        for col in range(12):
            x0, y0 = col * (w // 12), row * (h // 8)
            x1, y1 = x0 + w // 14, y0 + h // 10
            draw.rectangle([x0, y0, x1, y1], fill=(20, 20, 20))
    img.save(tmp.name)
    return Path(tmp.name)


def _make_clean_image(w: int = 200, h: int = 150) -> Path:
    """Moderate whitespace, centred content — should be clean."""
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Small centred block  — ~10% occupied, balanced
    bx0, by0 = w // 2 - 15, h // 2 - 15
    bx1, by1 = w // 2 + 15, h // 2 + 15
    draw.rectangle([bx0, by0, bx1, by1], fill=(80, 80, 80))
    img.save(tmp.name)
    return Path(tmp.name)


# ── whitespace tests ─────────────────────────────────────────────────────────

def test_all_white_warns():
    path = _make_white()
    result = compute_visual_metrics([path])
    ws_issues = [i for i in result.issues if i.metric == "whitespace"]
    assert ws_issues, "all-white image should produce a whitespace issue"
    assert ws_issues[0].severity == "warn"
    assert result.per_slide[1]["whitespace"] > 0.99


def test_all_black_warns():
    path = _make_black()
    result = compute_visual_metrics([path])
    ws_issues = [i for i in result.issues if i.metric == "whitespace"]
    assert ws_issues, "all-black image should produce a whitespace issue"
    assert result.per_slide[1]["whitespace"] < 0.01


# ── balance tests ─────────────────────────────────────────────────────────────

def test_centered_content_no_balance_issue():
    path = _make_centered_block()
    result = compute_visual_metrics([path], balance_threshold=0.15)
    bal_issues = [i for i in result.issues if i.metric == "balance"]
    assert not bal_issues, "centred block should not trigger balance warning"


def test_offcenter_content_balance_warns():
    path = _make_bottom_right_block()
    result = compute_visual_metrics([path], balance_threshold=0.15)
    bal_issues = [i for i in result.issues if i.metric == "balance"]
    assert bal_issues, "bottom-right block should trigger balance warning"
    assert bal_issues[0].severity == "warn"


# ── collision tests ───────────────────────────────────────────────────────────

def test_sparse_rects_no_collision():
    path = _make_sparse_rects()
    result = compute_visual_metrics([path], collision_max_pairs=0)
    col_issues = [i for i in result.issues if i.metric == "collision"]
    assert not col_issues, "sparse rectangles should not trigger collision warning"


def test_dense_rects_collision_warns():
    path = _make_dense_rects()
    result = compute_visual_metrics([path], collision_max_pairs=0)
    col_issues = [i for i in result.issues if i.metric == "collision"]
    assert col_issues, "dense rectangles should trigger collision warning"
    assert result.per_slide[1]["collision_pairs"] > 0


# ── verdict test ──────────────────────────────────────────────────────────────

def test_clean_image_returns_clean_verdict():
    path = _make_clean_image()
    result = compute_visual_metrics(
        [path],
        whitespace_range=(0.25, 0.99),
        balance_threshold=0.15,
        collision_max_pairs=4,  # allow a few dense cells around a centred block
    )
    assert isinstance(result, VisualMetricsResult)
    assert result.verdict == "clean", (
        f"Expected clean, got {result.verdict}; issues: {result.issues}"
    )


# ── multi-slide dict input ────────────────────────────────────────────────────

def test_dict_input_keys_preserved():
    p1 = _make_white()
    p3 = _make_centered_block()
    result = compute_visual_metrics({1: p1, 3: p3})
    assert 1 in result.per_slide
    assert 3 in result.per_slide
    assert 2 not in result.per_slide


# ── report writer ─────────────────────────────────────────────────────────────

def test_write_report():
    p1 = _make_white()
    p2 = _make_bottom_right_block()
    result = compute_visual_metrics(
        {1: p1, 2: p2},
        whitespace_range=(0.25, 0.65),
        balance_threshold=0.15,
    )
    with tempfile.TemporaryDirectory() as tmp:
        report_path = Path(tmp) / "report.md"
        write_visual_metrics_report(result, report_path)
        text = report_path.read_text()

    assert "# Visual Metrics Report" in text
    assert "Whitespace" in text
    assert "Balance" in text
    assert "| 1 |" in text
    assert "| 2 |" in text
    assert "**Verdict:**" in text
