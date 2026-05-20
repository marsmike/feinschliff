from lib.defects import Defect, DefectKind, Severity
from lib.verify.autofix import suggest_fix


def test_slot_overflow_emits_chars_to_drop():
    d = Defect(
        slide_index=2,
        kind=DefectKind.SLOT_OVERFLOW,
        severity=Severity.FATAL,
        message="slot 'body' is 142 chars over budget",
        meta={"slot": "body", "actual_chars": 480, "budget_chars": 338, "over_by": 142},
    )
    fix = suggest_fix(d)
    assert fix is not None
    assert fix["slide_index"] == 2
    assert fix["slot"] == "body"
    assert fix["action"] == "shorten"
    assert fix["target_chars"] == 338
    assert "drop ~142 chars" in fix["instruction"].lower()


def test_text_overlap_emits_truncate_for_offending_shape():
    d = Defect(
        slide_index=4,
        kind=DefectKind.TEXT_OVERLAP,
        severity=Severity.FATAL,
        message="title overlaps subtitle",
        meta={"a_id": "title", "b_id": "subtitle", "overlap_px": 28},
    )
    fix = suggest_fix(d)
    assert fix is not None
    assert fix["action"] == "shorten"
    assert fix["slot"] in {"title", "subtitle"}


def test_filler_word_emits_remove_word_instruction():
    d = Defect(
        slide_index=1,
        kind=DefectKind.FILLER_WORD,
        severity=Severity.WARN,
        message="filler word 'really' in slot 'body'",
        meta={"slot": "body", "word": "really", "char_index": 73},
    )
    fix = suggest_fix(d)
    assert fix["action"] == "delete_word"
    assert fix["word"] == "really"


def test_unknown_defect_returns_none():
    d = Defect(
        slide_index=1,
        kind=DefectKind.CHROME_DRIFT,
        severity=Severity.FATAL,
        message="footer drifted 12px between slides 1 and 2",
    )
    assert suggest_fix(d) is None
