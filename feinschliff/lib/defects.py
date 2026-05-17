"""Single source of truth for defect classes, severity, and reporting.

Every CLI entrypoint, validator, and verifier emits `Defect` records with
a `kind` drawn from `DefectKind` and a `severity` drawn from `Severity`.
`fatal_kinds()` is the canonical set of defect kinds that cause builds
and verifies to exit non-zero by default; CLI flags like
`--allow-diagram-warnings` and `--allow-missing-assets` shave individual
kinds off that set per invocation.
"""
from __future__ import annotations

import dataclasses
from enum import Enum
from typing import Any


class Severity(str, Enum):
    FATAL = "fatal"
    WARN = "warn"
    INFO = "info"


class DefectKind(str, Enum):
    # Geometry (layout_validator)
    TEXT_OVERLAP = "text-overlap"
    OUT_OF_BOUNDS = "out-of-bounds"
    SLOT_OVERFLOW = "slot-overflow"
    # Diagram (validate_diagrams* / structural_validator)
    DIAGRAM_OVERFLOW = "diagram-overflow"
    DIAGRAM_TEXT_TOO_SMALL = "diagram-text-too-small"
    DIAGRAM_COLOR_MISMATCH = "diagram-color-mismatch"
    DIAGRAM_SHAPE_OVERLAP = "diagram-shape-overlap"
    DIAGRAM_TEXT_COLLISION = "diagram-text-collision"
    DIAGRAM_ARROW_CROSSING = "diagram-arrow-crossing"
    DIAGRAM_INVALID_FILE = "diagram-invalid-file"
    # Chrome (verify/chrome.py)
    DROP_SHADOW = "drop-shadow"
    GRADIENT_FILL = "gradient-fill"
    FAT_OUTLINE = "fat-outline"
    CHROME_DRIFT = "chrome-drift"
    # Content (content_validator)
    TITLE_TOO_LONG = "title-too-long"
    FILLER_WORD = "filler-word"
    VAGUE_SO_WHAT = "vague-so-what"
    # LLM-judged (verify/llm)
    SQUINT_TEST = "squint-test"
    TITLE_BODY_COHERENCE = "title-body-coherence"
    CLAIM_TITLE = "claim-title"
    BULLET_DUMP = "bullet-dump"
    # DSL pipeline (pipeline.py)
    UNKNOWN_COMPOUND = "unknown-compound"
    # Asset policy (pptx_emit)
    MISSING_ASSET = "missing-asset"
    PLACEHOLDER_RECTANGLE = "placeholder-rectangle"


_FATAL: frozenset[str] = frozenset({
    DefectKind.TEXT_OVERLAP.value,
    DefectKind.OUT_OF_BOUNDS.value,
    DefectKind.UNKNOWN_COMPOUND.value,
    DefectKind.DIAGRAM_OVERFLOW.value,
    DefectKind.DIAGRAM_TEXT_TOO_SMALL.value,
    DefectKind.DIAGRAM_SHAPE_OVERLAP.value,
    DefectKind.DIAGRAM_TEXT_COLLISION.value,
    DefectKind.DIAGRAM_INVALID_FILE.value,
    # DIAGRAM_ARROW_CROSSING intentionally NOT fatal — the heuristic can
    # false-positive on arrows that route around a non-endpoint shape on
    # purpose. Surfaced as WARN; opt in to fatal via callsite if desired.
    DefectKind.DROP_SHADOW.value,
    DefectKind.GRADIENT_FILL.value,
    DefectKind.FAT_OUTLINE.value,
    DefectKind.CHROME_DRIFT.value,
    DefectKind.MISSING_ASSET.value,
})


def fatal_kinds() -> frozenset[str]:
    """Defect kinds that cause non-zero exit by default."""
    return _FATAL


@dataclasses.dataclass(frozen=True)
class Defect:
    slide_index: int
    kind: DefectKind
    severity: Severity
    message: str
    meta: dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slide_index": self.slide_index,
            "kind": self.kind.value,
            "severity": self.severity.value,
            "message": self.message,
            "meta": dict(self.meta),
        }


def format_defect(d: Defect) -> str:
    return (
        f"slide {d.slide_index}: [{d.severity.value.upper()}] "
        f"{d.kind.value} — {d.message}"
    )
