"""Deterministic plan lint — the cheap gate before any render.

Errors block the render (the plan would produce a broken or off-doctrine
edit); warnings are taste signals the author may override. Grows with the
template library: every new kind adds a REQUIRED_FIELDS row (a beat missing
its content fields renders blank, so lint refuses it up front).
"""
from __future__ import annotations

KNOWN_KINDS = {"hook_title", "word_pop", "stat_punch"}

# kind -> fields that render blank/broken when absent
REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "hook_title": ("title",),
    "word_pop": ("items",),
    "stat_punch": ("value", "caption"),
}

# Overlays ride on the speaker; takeovers replace the frame.
OVERLAY_KINDS = {"hook_title", "word_pop"}
# TODO(M2): add takeover-overlap check when a second takeover kind ships.
# Multi-item kinds where end_sec spans an enumeration (alignment never caps these).
SEQUENCE_KINDS = {"word_pop"}

FIRST_TAKEOVER_FLOOR = 1.5   # the viewer needs speaker face-time first
TEXT_VERTICAL_FLOOR = 0.58   # text never over the face
TEXT_VERTICAL_CEILING = 0.9  # text never off the bottom edge
DENSITY_WINDOW, DENSITY_CAP = 12.0, 4   # max beats per rolling window
HOOK_DEADLINE = 0.6          # hook visible inside the scroll-decision window

DEFAULT_VERTICAL = {"word_pop": 0.72, "hook_title": 0.66}


def _num(beat: dict, field: str) -> float | None:
    value = beat.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def lint_beats(beats: list[dict], duration: float) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for i, b in enumerate(beats):
        tag = f"beat {i} ({b.get('kind', '?')})"
        kind = b.get("kind")
        if kind not in KNOWN_KINDS:
            errors.append(f"{tag}: unknown kind '{kind}'")
            continue
        reason = b.get("reason")
        if not (isinstance(reason, str) and reason.strip()):
            errors.append(f"{tag}: missing 'reason' — every visual must mean "
                          "something specific; the reason field is the gate")
        for field in REQUIRED_FIELDS[kind]:
            value = b.get(field)
            if value is None or value == "" or value == []:
                errors.append(f"{tag}: missing required field '{field}' "
                              "(renders blank without it)")
        start = _num(b, "start_sec")
        end = _num(b, "end_sec")
        if start is None or start < 0 or end is None or end <= start:
            errors.append(f"{tag}: start_sec/end_sec invalid")
            continue
        if end > duration + 0.05:
            errors.append(f"{tag}: end_sec {end} exceeds video duration {duration}")
        if kind == "word_pop":
            items = b.get("items")
            if not isinstance(items, list):
                errors.append(f"{tag}: 'items' must be a list")
            else:
                for j, item in enumerate(items):
                    if not isinstance(item, dict):
                        errors.append(f"{tag}: items[{j}] must be an object with "
                                      "'text' + 'appear_sec'")
                    elif "text" not in item or "appear_sec" not in item:
                        errors.append(f"{tag}: items[{j}] needs 'text' + 'appear_sec' "
                                      "(absolute source-video seconds)")
                    else:
                        # start/end are valid here (invalid beats `continue` above).
                        appear = _num(item, "appear_sec")
                        if appear is not None and not (start <= appear < end):
                            errors.append(
                                f"{tag}: items[{j}] appear_sec {appear:g} outside the "
                                f"beat window [{start:g}, {end:g}) — the item would "
                                "never show (or shadow the whole beat)")
        if kind in OVERLAY_KINDS:
            if "vertical" in b:
                vertical = _num(b, "vertical")
                if vertical is None:
                    errors.append(f"{tag}: vertical must be a number")
            else:
                vertical = DEFAULT_VERTICAL[kind]
            if vertical is not None and vertical < TEXT_VERTICAL_FLOOR:
                errors.append(f"{tag}: vertical {vertical} < {TEXT_VERTICAL_FLOOR} "
                              "— text must never overlay the speaker's face")
            if vertical is not None and vertical > TEXT_VERTICAL_CEILING:
                errors.append(f"{tag}: vertical {vertical} > {TEXT_VERTICAL_CEILING} "
                              "— text would run off the bottom edge")

    timed = sorted((b for b in beats if b.get("kind") in KNOWN_KINDS
                    and _num(b, "start_sec") is not None
                    and _num(b, "end_sec") is not None),
                   key=lambda b: _num(b, "start_sec"))

    takeovers = [b for b in timed if b["kind"] not in OVERLAY_KINDS]
    if takeovers and takeovers[0]["start_sec"] < FIRST_TAKEOVER_FLOOR:
        errors.append(f"first takeover starts at {takeovers[0]['start_sec']}s — "
                      f"floor is {FIRST_TAKEOVER_FLOOR}s of speaker face-time "
                      "(hook_title overlay is exempt)")

    hooks = [b for b in timed if b["kind"] == "hook_title"]
    if not hooks:
        warnings.append("no hook_title beat — every edit should open with a "
                        "composed text hook inside the first 0.5s")
    elif hooks[0]["start_sec"] > HOOK_DEADLINE:
        warnings.append(f"hook_title starts at {hooks[0]['start_sec']}s — "
                        f"should be on screen within {HOOK_DEADLINE}s")

    for b in timed:
        window = [x for x in timed
                  if b["start_sec"] <= x["start_sec"] < b["start_sec"] + DENSITY_WINDOW]
        if len(window) > DENSITY_CAP:
            warnings.append(f"density: {len(window)} beats inside {DENSITY_WINDOW:g}s from "
                            f"{b['start_sec']}s — cap is {DENSITY_CAP}; drop the "
                            "lowest-priority beat")
            break

    return errors, warnings
