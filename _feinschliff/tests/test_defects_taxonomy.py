from lib.defects import (
    Defect, DefectKind, Severity, fatal_kinds, format_defect,
)


def test_defect_kind_enum_covers_known_classes():
    expected = {
        "text-overlap", "out-of-bounds",
        "diagram-overflow", "diagram-text-too-small", "diagram-color-mismatch",
        "drop-shadow", "gradient-fill", "fat-outline", "chrome-drift",
        "slot-overflow", "title-too-long", "filler-word", "vague-so-what",
        "squint-test", "title-body-coherence", "claim-title", "bullet-dump",
        "unknown-compound",
        "missing-asset", "placeholder-rectangle",
    }
    actual = {k.value for k in DefectKind}
    assert expected <= actual, f"missing: {expected - actual}"


def test_severity_policy_split_is_explicit():
    fatal = fatal_kinds()
    assert "out-of-bounds" in fatal
    assert "diagram-overflow" in fatal
    assert "missing-asset" in fatal
    assert "unknown-compound" in fatal
    assert "filler-word" not in fatal


def test_defect_dataclass_is_immutable_and_serializable():
    d = Defect(
        slide_index=3,
        kind=DefectKind.TEXT_OVERLAP,
        severity=Severity.FATAL,
        message="rectangle 'A' overlaps rectangle 'B'",
        meta={"a_id": "r1", "b_id": "r2"},
    )
    import dataclasses
    assert dataclasses.is_dataclass(d)
    payload = d.to_dict()
    assert payload["kind"] == "text-overlap"
    assert payload["severity"] == "fatal"
    assert payload["meta"]["a_id"] == "r1"


def test_format_defect_human_readable():
    d = Defect(
        slide_index=2,
        kind=DefectKind.SLOT_OVERFLOW,
        severity=Severity.WARN,
        message="slot 'body' is 142 chars over budget",
    )
    s = format_defect(d)
    assert "slide 2" in s
    assert "slot-overflow" in s
    assert "WARN" in s
