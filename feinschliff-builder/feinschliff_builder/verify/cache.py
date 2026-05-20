"""Per-slide content-hash cache for LLM verify rubrics.

Persisted at <deck_dir>/.verify_cache.json. Keyed by (slide_hash, rubric).
Cleared automatically when brand or layout changes because brand and layout
are part of the hash — a change produces a new key, and old entries become
unreachable (but are not pruned; acceptable for v1).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal


@dataclass
class CachedVerdict:
    slide_hash: str            # sha256 of normalised slide content + layout name + brand
    rubric: str                # "squint", "title-body", "claim-title", "bullet-dump"
    status: Literal["pass", "fail", "skipped"]
    findings: dict             # per-slide finding payload (the dict the rubric returned)
    cached_at: str             # ISO-8601 timestamp


class VerifyCache:
    """Persisted at <deck_dir>/.verify_cache.json.

    Keyed by ``"{slide_hash}:{rubric}"``. Load-on-init, save-on-demand via
    :meth:`save`.  Thread safety is not a goal for v1 (single-process CLI).
    """

    _FILENAME = ".verify_cache.json"

    def __init__(self, deck_dir: Path) -> None:
        self._path = deck_dir / self._FILENAME
        self._data: dict[str, dict] = {}
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self._data = raw
            except (json.JSONDecodeError, OSError):
                # Corrupt cache — start fresh; will be overwritten on next save.
                self._data = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, slide_hash: str, rubric: str) -> CachedVerdict | None:
        key = self._key(slide_hash, rubric)
        entry = self._data.get(key)
        if entry is None:
            return None
        try:
            return CachedVerdict(**entry)
        except TypeError:
            # Malformed entry — treat as miss.
            return None

    def put(self, verdict: CachedVerdict) -> None:
        key = self._key(verdict.slide_hash, verdict.rubric)
        self._data[key] = asdict(verdict)

    def save(self) -> None:
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _key(slide_hash: str, rubric: str) -> str:
        return f"{slide_hash}:{rubric}"


def slide_hash(slide: dict, brand: str) -> str:
    """Stable sha256 hex of (brand, layout, sorted(content.items())).

    Excludes ``_meta`` (informational) and ``slot_budgets`` (derived).
    Same content + same layout + same brand → same hash.
    """
    content = slide.get("content") or {}
    payload = {
        "brand": brand,
        "layout": slide.get("layout", ""),
        "content": json.dumps(content, sort_keys=True, ensure_ascii=False),
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
