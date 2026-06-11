"""Per-video workdir + stage-keyed cache markers.

Every pipeline stage is cached on exactly its own inputs (stage_key of those
inputs) and a marker is written ONLY after the stage fully succeeded — a
crash can never produce a false cache hit (design decision D5).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

CACHE_ROOT = Path.home() / ".cache" / "feinschnitt" / "edit"


def workdir_for(video: Path) -> Path:
    video = video.resolve()
    digest = hashlib.sha1(str(video).encode()).hexdigest()[:8]
    wd = CACHE_ROOT / f"{video.stem}-{digest}"
    wd.mkdir(parents=True, exist_ok=True)
    return wd


def stage_key(*parts: object) -> str:
    return hashlib.sha1("\x1f".join(str(p) for p in parts).encode()).hexdigest()


def stage_is_fresh(marker: Path, key: str) -> bool:
    return marker.exists() and marker.read_text().strip() == key


def mark_stage_done(marker: Path, key: str) -> None:
    marker.write_text(key)
