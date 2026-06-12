"""Unit tests for feinschliff_builder.verify.verify_map.load_verify_map."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from feinschliff_builder.verify.verify_map import VerifyMap, load_verify_map


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_map(tmp_path: Path, content: str) -> Path:
    """Write content to <tmp_path>/verify-map.yaml and return tmp_path."""
    (tmp_path / "verify-map.yaml").write_text(textwrap.dedent(content), encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_valid_layouts_only(tmp_path: Path) -> None:
    brand = _write_map(tmp_path, """\
        layouts:
          cover-dark: 1
          quote: 11
          table: 3
    """)
    vm = load_verify_map(brand)
    assert isinstance(vm, VerifyMap)
    assert vm.layouts == {"cover-dark": 1, "quote": 11, "table": 3}
    assert vm.chart_bboxes == {}


def test_valid_with_chart_bboxes(tmp_path: Path) -> None:
    brand = _write_map(tmp_path, """\
        layouts:
          quote: 11
          timeline: 4
        chart_bboxes:
          quote: [75, 195, 1770, 410]
          timeline: [55, 165, 1810, 660]
    """)
    vm = load_verify_map(brand)
    assert vm.layouts == {"quote": 11, "timeline": 4}
    assert vm.chart_bboxes == {
        "quote": [75, 195, 1770, 410],
        "timeline": [55, 165, 1810, 660],
    }


def test_layouts_values_coerced_to_int(tmp_path: Path) -> None:
    """YAML may parse bare integers correctly; string-encoded numbers also work."""
    brand = _write_map(tmp_path, """\
        layouts:
          cover: 1
    """)
    vm = load_verify_map(brand)
    assert isinstance(vm.layouts["cover"], int)


def test_chart_bboxes_values_coerced_to_int(tmp_path: Path) -> None:
    brand = _write_map(tmp_path, """\
        layouts:
          cover: 1
        chart_bboxes:
          cover: [0, 0, 1920, 1080]
    """)
    vm = load_verify_map(brand)
    assert all(isinstance(v, int) for v in vm.chart_bboxes["cover"])


def test_null_chart_bboxes_treated_as_empty(tmp_path: Path) -> None:
    """chart_bboxes: null (or absent) → empty dict, no error."""
    brand = _write_map(tmp_path, """\
        layouts:
          cover: 1
        chart_bboxes:
    """)
    vm = load_verify_map(brand)
    assert vm.chart_bboxes == {}


# ---------------------------------------------------------------------------
# Missing file
# ---------------------------------------------------------------------------

def test_missing_file_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="missing verify-map.yaml"):
        load_verify_map(tmp_path)


# ---------------------------------------------------------------------------
# Malformed YAML
# ---------------------------------------------------------------------------

def test_malformed_yaml_raises_value_error(tmp_path: Path) -> None:
    (tmp_path / "verify-map.yaml").write_text(":\n  :\n  bad: [unclosed", encoding="utf-8")
    with pytest.raises(ValueError, match="malformed YAML"):
        load_verify_map(tmp_path)


def test_yaml_not_a_mapping_raises_value_error(tmp_path: Path) -> None:
    (tmp_path / "verify-map.yaml").write_text("- item1\n- item2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="expected a YAML mapping"):
        load_verify_map(tmp_path)


# ---------------------------------------------------------------------------
# Wrong shape / missing keys
# ---------------------------------------------------------------------------

def test_missing_layouts_key_raises_value_error(tmp_path: Path) -> None:
    brand = _write_map(tmp_path, """\
        chart_bboxes:
          cover: [0, 0, 100, 100]
    """)
    with pytest.raises(ValueError, match="missing required key 'layouts'"):
        load_verify_map(brand)


def test_layouts_not_a_mapping_raises_value_error(tmp_path: Path) -> None:
    brand = _write_map(tmp_path, """\
        layouts:
          - cover
          - quote
    """)
    with pytest.raises(ValueError, match="'layouts' must be a mapping"):
        load_verify_map(brand)


def test_layout_non_integer_slide_number_raises_value_error(tmp_path: Path) -> None:
    brand = _write_map(tmp_path, """\
        layouts:
          cover: not-a-number
    """)
    with pytest.raises(ValueError, match="non-integer slide number"):
        load_verify_map(brand)


def test_layout_zero_slide_number_raises_value_error(tmp_path: Path) -> None:
    brand = _write_map(tmp_path, """\
        layouts:
          cover: 0
    """)
    with pytest.raises(ValueError, match="must be ≥ 1"):
        load_verify_map(brand)


def test_layout_negative_slide_number_raises_value_error(tmp_path: Path) -> None:
    brand = _write_map(tmp_path, """\
        layouts:
          cover: -1
    """)
    with pytest.raises(ValueError, match="must be ≥ 1"):
        load_verify_map(brand)


def test_chart_bboxes_not_a_mapping_raises_value_error(tmp_path: Path) -> None:
    brand = _write_map(tmp_path, """\
        layouts:
          cover: 1
        chart_bboxes: [0, 0, 100, 100]
    """)
    with pytest.raises(ValueError, match="'chart_bboxes' must be a mapping"):
        load_verify_map(brand)


def test_chart_bbox_wrong_length_raises_value_error(tmp_path: Path) -> None:
    brand = _write_map(tmp_path, """\
        layouts:
          cover: 1
        chart_bboxes:
          cover: [0, 0, 100]
    """)
    with pytest.raises(ValueError, match="list of 4 integers"):
        load_verify_map(brand)


def test_chart_bbox_non_integer_raises_value_error(tmp_path: Path) -> None:
    brand = _write_map(tmp_path, """\
        layouts:
          cover: 1
        chart_bboxes:
          cover: [0, 0, "wide", 100]
    """)
    with pytest.raises(ValueError, match="non-integer"):
        load_verify_map(brand)
