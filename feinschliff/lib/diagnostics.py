"""DiagnosticBag — typed collection for linting and verification results.

This module introduces first-class types for the diagnostic layer:

- :class:`Severity` — INFO / WARNING / ERROR
- :class:`DefectKind` — all known defect categories
- :class:`Defect` — immutable defect record
- :class:`DiagnosticBag` — ordered, filterable collection of Defects

``lib.defects`` re-exports these types for backwards compatibility; existing
imports of ``from lib.defects import Defect, DefectKind, Severity`` continue
to work unchanged.

The Severity and DefectKind enums in this module are designed to be additive
supersets of the values in ``lib.defects``.  The existing ``Severity`` in
``lib.defects`` uses (FATAL / WARN / INFO) while this module uses the more
conventional (ERROR / WARNING / INFO).  Both modules co-exist during the
migration; ``DiagnosticBag`` uses the new Severity.  The legacy ``Defect``
dataclass in ``lib.defects`` retains its own Severity enum for backwards
compatibility.
"""
from __future__ import annotations

import dataclasses
from enum import Enum
from typing import Any, Iterator


class Severity(str, Enum):
    """Diagnostic severity level."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class DefectKind(str, Enum):
    """All known defect categories.

    Superset of the kinds in ``lib.defects.DefectKind``.  New kinds added
    here should be documented with a comment describing the check.
    """
    # --- Geometry (layout_validator) ---
    LAYOUT_OVERLAP = "text-overlap"          # text boxes overlap each other
    LAYOUT_OUT_OF_BOUNDS = "out-of-bounds"   # element outside slide canvas
    LAYOUT_MISSING_SLOT = "empty-placeholder"  # required slot is empty
    SLOT_OVERFLOW = "slot-overflow"          # text overflows slot budget

    # --- Text quality ---
    TEXT_OVERFLOW = "slot-overflow"          # alias: same as SLOT_OVERFLOW
    TEXT_UNDERFLOW = "text-underflow"        # text too short for slot

    # --- Brand token ---
    BRAND_TOKEN_MISSING = "brand-token-missing"  # brand tokens.json missing expected key
    BRAND_FONT_MISSING = "brand-font-missing"    # font referenced in tokens not installed

    # --- Diagram ---
    DIAGRAM_INVALID_PRIMITIVE = "diagram-invalid-file"    # bad diagram DSL / invalid file
    DIAGRAM_STRUCTURAL = "diagram-shape-overlap"          # structural layout defect in diagram
    DIAGRAM_OVERFLOW = "diagram-overflow"                 # diagram spills outside its slot
    DIAGRAM_TEXT_TOO_SMALL = "diagram-text-too-small"     # text below legibility threshold
    DIAGRAM_COLOR_MISMATCH = "diagram-color-mismatch"     # colour not in brand palette
    DIAGRAM_TEXT_COLLISION = "diagram-text-collision"     # labels overlap
    DIAGRAM_ARROW_CROSSING = "diagram-arrow-crossing"     # arrows cross each other
    DIAGRAM_ARROW_CROSS_ZONE_UNROUTED = "diagram-arrow-cross-zone-unrouted"

    # --- Chrome (visual fidelity) ---
    DROP_SHADOW = "drop-shadow"
    GRADIENT_FILL = "gradient-fill"
    FAT_OUTLINE = "fat-outline"
    CHROME_DRIFT = "chrome-drift"

    # --- Content (content_validator) ---
    TITLE_TOO_LONG = "title-too-long"
    FILLER_WORD = "filler-word"
    VAGUE_SO_WHAT = "vague-so-what"

    # --- LLM-judged (verify/llm) ---
    SQUINT_TEST = "squint-test"
    TITLE_BODY_COHERENCE = "title-body-coherence"
    CLAIM_TITLE = "claim-title"
    BULLET_DUMP = "bullet-dump"

    # --- DSL pipeline ---
    UNKNOWN_COMPOUND = "unknown-compound"

    # --- Asset policy (pptx_emit) ---
    MISSING_ASSET = "missing-asset"
    PLACEHOLDER_RECTANGLE = "placeholder-rectangle"

    # --- Image quality (image_preflight) ---
    IMAGE_PALETTE_CLASH = "image-palette-clash"
    IMAGE_CROP_RISK = "image-crop-risk"

    # --- Catch-all ---
    INTERNAL = "internal"


# ---------------------------------------------------------------------------
# Defect record
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class Defect:
    """One diagnostic finding.

    Parameters
    ----------
    kind:
        Machine-readable defect category.
    severity:
        How serious the finding is.
    message:
        Human-readable description.
    location:
        Optional context string, e.g. ``'slide 3'`` or ``'brands/feinschliff'``.
    suggestion:
        Optional fix hint.
    extra:
        Arbitrary extra metadata dict (serialisable).
    """
    kind: DefectKind
    severity: Severity
    message: str
    location: str | None = None
    suggestion: str | None = None
    extra: dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "kind": self.kind.value,
            "severity": self.severity.value,
            "message": self.message,
        }
        if self.location is not None:
            d["location"] = self.location
        if self.suggestion is not None:
            d["suggestion"] = self.suggestion
        if self.extra:
            d["extra"] = dict(self.extra)
        return d


# ---------------------------------------------------------------------------
# DiagnosticBag
# ---------------------------------------------------------------------------

class DiagnosticBag:
    """Ordered, filterable collection of :class:`Defect` objects.

    Usage::

        bag = DiagnosticBag()
        bag.add(Defect(DefectKind.BRAND_TOKEN_MISSING, Severity.ERROR, "missing token"))
        if bag.has_errors():
            print(f"{len(bag)} error(s)")
        for d in bag.by_severity(Severity.ERROR):
            print(d.message)
    """

    def __init__(self) -> None:
        self._defects: list[Defect] = []

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add(self, defect: Defect) -> None:
        """Append one defect to the bag."""
        if not isinstance(defect, Defect):
            raise TypeError(f"expected Defect, got {type(defect).__name__}")
        self._defects.append(defect)

    def extend(self, other: "DiagnosticBag | list[Defect]") -> None:
        """Merge another bag (or list of Defects) into this one."""
        if isinstance(other, DiagnosticBag):
            self._defects.extend(other._defects)
        else:
            for d in other:
                self.add(d)

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def by_severity(self, severity: Severity) -> list[Defect]:
        """Return all defects with the given severity, in insertion order."""
        return [d for d in self._defects if d.severity is severity]

    def has_errors(self) -> bool:
        """True when at least one ERROR-severity defect is present."""
        return any(d.severity is Severity.ERROR for d in self._defects)

    def has_only_warnings(self) -> bool:
        """True when there are defects but none are ERROR-severity."""
        return bool(self._defects) and not self.has_errors()

    def to_list(self) -> list[dict[str, Any]]:
        """Serialise all defects to a list of dicts."""
        return [d.to_dict() for d in self._defects]

    # ------------------------------------------------------------------
    # Standard collection protocol
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._defects)

    def __iter__(self) -> Iterator[Defect]:
        return iter(self._defects)

    def __bool__(self) -> bool:
        return bool(self._defects)

    def __repr__(self) -> str:
        errors = len(self.by_severity(Severity.ERROR))
        warnings = len(self.by_severity(Severity.WARNING))
        return f"DiagnosticBag(errors={errors}, warnings={warnings}, total={len(self)})"
