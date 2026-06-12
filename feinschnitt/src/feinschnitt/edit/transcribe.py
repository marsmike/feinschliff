"""Word-timestamped transcription → <workdir>/words.json.

words.json format:
  {"source": "<abs path>", "duration": 47.2,
   "words": [{"w": "Claude", "s": 1.23, "e": 1.51}, ...]}

This file is the timing source of truth for the whole edit: speech anchors,
appear_sec values, captions, and zoom heuristics all read it.
"""
from __future__ import annotations

import json
from pathlib import Path

from feinschnitt.edit import EditError
from feinschnitt.edit import corrections
from feinschnitt.edit.workdir import (
    mark_stage_done,
    stage_is_fresh,
    stage_key,
    workdir_for,
)


def _load_model(model_size: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise EditError(
            "faster-whisper is not installed — install the edit extra: "
            "uv pip install 'feinschnitt[edit]'"
        ) from exc
    try:
        return WhisperModel(model_size, compute_type="auto")
    except Exception as exc:
        raise EditError(f"failed to load transcription model '{model_size}': {exc}") from exc


def transcribe(video: Path, model_size: str = "small") -> dict:
    if not video.exists():
        raise EditError(f"video not found: {video}")
    model = _load_model(model_size)
    try:
        segments, info = model.transcribe(str(video), word_timestamps=True)
        words = [
            {"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)}
            for seg in segments
            for w in (seg.words or [])
        ]
        duration = round(float(info.duration), 3)
    except EditError:
        raise
    except Exception as exc:
        raise EditError(f"transcription failed for {video.name}: {exc}") from exc
    return {
        "source": str(video.resolve()),
        "duration": duration,
        "words": corrections.apply_corrections(words),
    }


def run(video: Path, model_size: str = "small") -> Path:
    if not video.exists():
        raise EditError(f"video not found: {video}")
    wd = workdir_for(video)
    out = wd / "words.json"
    marker = wd / ".transcribed"
    key = stage_key(video.resolve(), video.stat().st_mtime_ns, model_size,
                    corrections.fingerprint())
    if stage_is_fresh(marker, key) and out.exists():
        return out
    data = transcribe(video, model_size)
    out.write_text(json.dumps(data, indent=2))
    mark_stage_done(marker, key)
    return out
