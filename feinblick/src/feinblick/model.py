"""The feinblick normalization vocabulary — the load-bearing spine."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import StrEnum


class Domain(StrEnum):
    CODE = "code"
    SKILL = "skill"


class Category(StrEnum):
    DEAD_CODE = "dead_code"
    DUPLICATION = "duplication"
    CIRCULAR_DEP = "circular_dep"
    COMPLEXITY = "complexity"
    BOUNDARY = "boundary"
    PROGRESSIVE_DISCLOSURE = "progressive_disclosure"
    FRONTMATTER = "frontmatter"
    DESCRIPTION = "description"
    HOOK = "hook"
    MCP = "mcp"
    REPO_DISCIPLINE = "repo_discipline"
    HEALTH_SCORE = "health_score"


# Engine severity strings (any casing) normalized onto our three levels.
_ENGINE_SEVERITY = {
    "critical": "error",
    "high": "error",
    "error": "error",
    "medium": "warning",
    "warning": "warning",
    "low": "info",
    "info": "info",
    "note": "info",
}


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    @property
    def rank(self) -> int:                       # for max()/reconciliation
        return {"error": 3, "warning": 2, "info": 1}[self.value]

    @property
    def sarif_level(self) -> str:
        return {"error": "error", "warning": "warning", "info": "note"}[self.value]

    @classmethod
    def from_engine(cls, value: str) -> Severity:
        """Normalize an engine severity string of any casing onto our levels.

        Maps CRITICAL/HIGH/error -> ERROR, MEDIUM/WARNING -> WARNING,
        LOW/INFO/note -> INFO. Unknown strings degrade to WARNING.
        """
        return cls(_ENGINE_SEVERITY.get((value or "").strip().lower(), "warning"))


@dataclass(frozen=True)
class Location:
    path: str                                    # repo-relative when possible
    line: int | None = None
    col: int | None = None
    symbol: str | None = None                    # content-anchored identity

    def to_dict(self) -> dict:
        return {"path": self.path, "line": self.line, "col": self.col, "symbol": self.symbol}


@dataclass(frozen=True)
class Action:
    description: str
    auto_fixable: bool = False
    engine_fix_cmd: str | None = None

    def to_dict(self) -> dict:
        return {"description": self.description, "auto_fixable": self.auto_fixable,
                "engine_fix_cmd": self.engine_fix_cmd}


@dataclass
class Finding:
    domain: Domain
    category: Category
    severity: Severity
    location: Location
    message: str
    source_engine: str
    rule_id: str | None = None
    evidence: str | None = None
    actions: list[Action] = field(default_factory=list)

    @property
    def fingerprint(self) -> str:
        return fingerprint(self)

    def to_dict(self) -> dict:
        return {
            "domain": self.domain.value, "category": self.category.value,
            "severity": self.severity.value, "location": self.location.to_dict(),
            "message": self.message, "evidence": self.evidence,
            "rule_id": self.rule_id, "source_engine": self.source_engine,
            "actions": [a.to_dict() for a in self.actions],
            "fingerprint": self.fingerprint,
        }


_NUM = re.compile(r"\d+")


def _digest(text: str | None) -> str:
    """Number-insensitive digest of free text (so 'McCabe=6' == 'McCabe=9')."""
    if not text:
        return ""
    return _NUM.sub("#", text).strip().lower()


def fingerprint(f: Finding) -> str:
    """Stable identity key: excludes absolute line numbers; anchors on symbol."""
    loc = f.location
    norm_loc = f"{loc.path}::{loc.symbol or ''}"
    parts = [
        f.category.value, f.source_engine, f.rule_id or "", norm_loc,
        _digest(f.evidence or f.message),
    ]
    return hashlib.sha1(" ".join(parts).encode("utf-8")).hexdigest()[:16]
