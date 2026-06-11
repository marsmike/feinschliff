"""Assemble props.json — the single data contract the Remotion engine reads."""
from __future__ import annotations

from feinschnitt.edit.lint import DEFAULT_VERTICAL


def build_props(source_path: str, aligned_plan: dict, zoom_plan: list[dict],
                theme: dict, meta: dict, fps: int = 30) -> dict:
    beats = []
    for beat in aligned_plan["beats"]:
        b = dict(beat)
        default = DEFAULT_VERTICAL.get(b.get("kind"))
        if default is not None and "vertical" not in b:
            b["vertical"] = default
        beats.append(b)
    return {
        "source": source_path,
        "durationSec": meta["duration"],
        "width": meta["width"],
        "height": meta["height"],
        "fps": fps,
        "beats": beats,
        "zoom": zoom_plan,
        "theme": theme,
    }
