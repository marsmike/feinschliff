"""Assemble props.json — the single data contract the Remotion engine reads."""
from __future__ import annotations


def build_props(source_path: str, aligned_plan: dict, zoom_plan: list[dict],
                theme: dict, meta: dict, fps: int = 30) -> dict:
    return {
        "source": source_path,
        "durationSec": meta["duration"],
        "width": meta["width"],
        "height": meta["height"],
        "fps": fps,
        "beats": aligned_plan["beats"],
        "zoom": zoom_plan,
        "theme": theme,
    }
