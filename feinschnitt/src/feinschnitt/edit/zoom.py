"""Zoom punch-in heuristic — subtle speaker emphasis every ~7s.

Windows open on sentence starts (gap >=0.5s or terminal punctuation on the
previous word); sentences containing digits get the stronger 1.08 punch.
The derived zoom_plan.json is hand-editable before render.
"""
from __future__ import annotations

import re

MIN_SPACING = 7.0
WINDOW = 2.5
SCALE, SCALE_STRONG = 1.06, 1.08


def build_zoom_plan(words: list[dict]) -> list[dict]:
    plan: list[dict] = []
    last_start = -1e9
    for k, word in enumerate(words):
        prev = words[k - 1] if k else None
        starts_sentence = (prev is None
                           or prev["w"].rstrip().endswith((".", "?", "!"))
                           or word["s"] - prev["e"] >= 0.5)
        if not starts_sentence or word["s"] - last_start < MIN_SPACING:
            continue
        lookahead = words[k:k + 8]
        strong = any(re.search(r"\d", w["w"]) for w in lookahead)
        plan.append({"start_sec": round(word["s"], 3),
                     "end_sec": round(word["s"] + WINDOW, 3),
                     "scale": SCALE_STRONG if strong else SCALE})
        last_start = word["s"]
    return plan
