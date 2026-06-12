"""Deterministic plan lint — the cheap gate before any render.

Errors block the render (the plan would produce a broken or off-doctrine
edit); warnings are taste signals the author may override. Grows with the
template library: every new kind adds a REQUIRED_FIELDS row (a beat missing
its content fields renders blank, so lint refuses it up front).
"""
from __future__ import annotations

from pathlib import Path

KNOWN_KINDS = {
    "hook_title",
    "word_pop",
    "stat_punch",
    "quote_pull",
    "static",
    "image_card",
    "vertical_timeline",
    "ratio_dots",
    "inline_chart",
}

# kind -> fields that render blank/broken when absent
REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "hook_title": ("title",),
    "word_pop": ("items",),
    "stat_punch": ("value", "caption"),
    "quote_pull": ("quote_text",),
    "static": ("image_path",),
    "image_card": ("image_path",),
    "vertical_timeline": ("steps",),
    "ratio_dots": ("total", "marked", "polarity", "mark_at"),
    "inline_chart": ("title", "data"),
}

# Overlays ride on the speaker; takeovers replace the frame.
# Note: takeover-overlap is handled by the engine's coverage underlay (M2 Task 4).
# Mirror: KNOWN_KINDS − OVERLAY_KINDS must equal TAKEOVER_KINDS in
# feinschnitt/edit-engine/src/EditedVideo.tsx — update both when adding a kind.
OVERLAY_KINDS = {"hook_title", "word_pop", "image_card", "ratio_dots", "inline_chart"}
# Multi-item kinds where end_sec spans an enumeration (alignment never caps these).
SEQUENCE_KINDS = {"word_pop", "vertical_timeline"}
# Kinds that require a local image file.
IMAGE_KINDS = {"static", "image_card"}
# Kinds whose text content has meaningful reading-time constraints.
# hook_title is intentionally excluded: short punchy hooks are doctrine-legal at 2s.
READING_TIME_KINDS = {"stat_punch", "quote_pull"}

FIRST_TAKEOVER_FLOOR = 1.5   # the viewer needs speaker face-time first
TEXT_VERTICAL_FLOOR = 0.58   # overlay never over the face
TEXT_VERTICAL_CEILING = 0.9  # overlay never off the bottom edge
DENSITY_WINDOW, DENSITY_CAP = 12.0, 4   # max beats per rolling window
HOOK_DEADLINE = 0.6          # hook visible inside the scroll-decision window

READ_CPS = 12.0      # comfortable scan speed for big typography
READ_DWELL = 1.5
READ_FLOOR = 3.5
IMAGE_BREATH = 1.5   # speaker breathing room between image beats

# Three places must agree per kind: this dict, props.py injection, and the
# template's fallback — update all when adding an overlay kind.
DEFAULT_VERTICAL = {"word_pop": 0.72, "hook_title": 0.66}


def _num(beat: dict, field: str) -> float | None:
    value = beat.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _text_of(beat: dict) -> str:
    """Concatenate all readable text fields of a beat for reading-time estimation."""
    parts = []
    for key in ("title", "kicker", "value", "caption", "quote_text"):
        v = beat.get(key)
        if v is None or isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            parts.append(str(v))
        elif isinstance(v, str) and v:
            parts.append(v)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Per-kind structure helpers — each returns list[str] of error messages.
# ---------------------------------------------------------------------------

def _check_item_list(
    beat: dict,
    tag: str,
    field: str,
    entry_fields: tuple[str, str],
    entry_label: str,
    start: float,
    end: float,
) -> list[str]:
    """Shared validator for word_pop items and vertical_timeline steps."""
    errs: list[str] = []
    entries = beat.get(field)
    if not isinstance(entries, list):
        errs.append(f"{tag}: '{field}' must be a list")
        return errs
    heading_field, appear_field = entry_fields
    for j, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errs.append(
                f"{tag}: {field}[{j}] must be an object with "
                f"'{heading_field}' + '{appear_field}'"
            )
            continue
        appear = _num(entry, appear_field)

        if field == "items":
            # word_pop: one message when either key is absent
            if "text" not in entry or appear_field not in entry:
                errs.append(
                    f"{tag}: {field}[{j}] needs 'text' + 'appear_sec' "
                    "(absolute source-video seconds)"
                )
            elif appear is not None and not (start <= appear < end):
                errs.append(
                    f"{tag}: {field}[{j}] appear_sec {appear:g} outside the "
                    f"beat window [{start:g}, {end:g}) — the item would "
                    "never show (or shadow the whole beat)"
                )
        else:
            # vertical_timeline steps: deduplicate by emitting one structural
            # message when heading or appear_sec is invalid, then separately
            # check the window.
            has_heading = isinstance(entry.get(heading_field), str) and entry.get(heading_field)
            if not has_heading or appear is None:
                errs.append(
                    f"{tag}: {field}[{j}] must be an object with "
                    f"'{heading_field}' + '{appear_field}'"
                )
            elif not (start <= appear < end):
                errs.append(
                    f"{tag}: {field}[{j}] appear_sec {appear:g} outside the "
                    f"beat window [{start:g}, {end:g}) — the item would "
                    "never show (or shadow the whole beat)"
                )
    return errs


def _check_word_pop(beat: dict, tag: str, start: float, end: float) -> list[str]:
    return _check_item_list(
        beat, tag, "items", ("text", "appear_sec"), "item", start, end
    )


def _check_vertical_timeline(beat: dict, tag: str, start: float, end: float) -> list[str]:
    return _check_item_list(
        beat, tag, "steps", ("heading", "appear_sec"), "step", start, end
    )


def _check_ratio_dots(beat: dict, tag: str, start: float, end: float) -> list[str]:
    errs: list[str] = []
    total = _num(beat, "total")
    marked = _num(beat, "marked")
    if total is None:
        errs.append(f"{tag}: 'total' must be a positive number")
    elif total <= 0:
        errs.append(f"{tag}: 'total' must be a positive number")
    if marked is None:
        errs.append(f"{tag}: 'marked' must be a number")
    elif marked < 0:
        errs.append(f"{tag}: 'marked' must be a number >= 0")
    if total is not None and marked is not None and marked > total:
        errs.append(f"{tag}: marked {marked:g} exceeds total {total:g}")
    polarity = beat.get("polarity")
    if polarity not in ("positive", "negative"):
        errs.append(f"{tag}: 'polarity' must be 'positive' or 'negative'")
    mark_at = _num(beat, "mark_at")
    if mark_at is None:
        errs.append(f"{tag}: 'mark_at' must be a number")
    elif not (start <= mark_at < end):
        errs.append(
            f"{tag}: mark_at {mark_at:g} outside the "
            f"beat window [{start:g}, {end:g})"
        )
    return errs


def _check_inline_chart(beat: dict, tag: str, start: float, end: float) -> list[str]:
    errs: list[str] = []
    data = beat.get("data")
    if not isinstance(data, list) or len(data) < 2:
        errs.append(f"{tag}: data must be a list of at least 2 numbers")
    elif not all(
        not isinstance(v, bool) and isinstance(v, (int, float))
        for v in data
    ):
        errs.append(f"{tag}: data must be a list of at least 2 numbers")
    return errs


_KIND_CHECKS = {
    "word_pop": _check_word_pop,
    "vertical_timeline": _check_vertical_timeline,
    "ratio_dots": _check_ratio_dots,
    "inline_chart": _check_inline_chart,
}


def lint_beats(
    beats: list[dict],
    duration: float,
    base_dir: Path | None = None,
) -> tuple[list[str], list[str]]:
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

        if kind in _KIND_CHECKS:
            errors.extend(_KIND_CHECKS[kind](b, tag, start, end))

        if kind in IMAGE_KINDS:
            image_path = b.get("image_path")
            if not (isinstance(image_path, str) and image_path):
                errors.append(f"{tag}: 'image_path' must be a non-empty string")
            elif not Path(image_path).suffix:
                errors.append(f"{tag}: image_path has no file extension — "
                              "the engine cannot infer a MIME type")
            elif base_dir is not None:
                p = Path(image_path)
                resolved = p if p.is_absolute() else base_dir / p
                if not resolved.is_file():
                    errors.append(f"{tag}: image not found: {resolved}")

        if kind in OVERLAY_KINDS:
            if "vertical" in b:
                vertical = _num(b, "vertical")
                if vertical is None:
                    errors.append(f"{tag}: vertical must be a number")
            else:
                vertical = DEFAULT_VERTICAL.get(kind)
            if vertical is not None and vertical < TEXT_VERTICAL_FLOOR:
                errors.append(f"{tag}: vertical {vertical} < {TEXT_VERTICAL_FLOOR} "
                              "— overlay content must never cover the speaker's face")
            if vertical is not None and vertical > TEXT_VERTICAL_CEILING:
                errors.append(f"{tag}: vertical {vertical} > {TEXT_VERTICAL_CEILING} "
                              "— text would run off the bottom edge")

        if kind in READING_TIME_KINDS:
            text = _text_of(b)
            beat_duration = end - start
            ideal = max(READ_FLOOR, len(text) / READ_CPS + READ_DWELL)
            if beat_duration < 0.7 * ideal:
                warnings.append(
                    f"{tag}: beat is {beat_duration:.1f}s but the viewer can't finish "
                    f"reading {len(text)} chars — ideal is {ideal:.1f}s")
            elif beat_duration > 1.8 * ideal:
                warnings.append(
                    f"{tag}: beat is {beat_duration:.1f}s — text lingers "
                    f"(ideal {ideal:.1f}s); consider trimming or adding a beat")

    timed = sorted(
        (b for b in beats
         if b.get("kind") in KNOWN_KINDS
         and _num(b, "start_sec") is not None
         and _num(b, "end_sec") is not None),
        key=lambda b: _num(b, "start_sec"),
    )

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

    # Image breathing room: consecutive image beats that are too close together
    # read as a slideshow and don't give the speaker time to land the visual.
    image_timed = [b for b in timed if b.get("kind") in IMAGE_KINDS]
    for idx, (prev, nxt) in enumerate(zip(image_timed, image_timed[1:])):
        prev_end = _num(prev, "end_sec")
        nxt_start = _num(nxt, "start_sec")
        if prev_end is not None and nxt_start is not None:
            gap = nxt_start - prev_end
            if gap < IMAGE_BREATH:
                prev_i = beats.index(prev)
                nxt_i = beats.index(nxt)
                warnings.append(
                    f"two image beats back-to-back read as a slideshow — "
                    f"beats {prev_i} ({prev.get('kind')} at {prev['start_sec']:g}s) and "
                    f"{nxt_i} ({nxt.get('kind')} at {nxt['start_sec']:g}s): "
                    f"give the speaker >={IMAGE_BREATH:g}s between them"
                )

    return errors, warnings
