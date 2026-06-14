"""Serialize a PickerReport to JSON."""
from __future__ import annotations

import json
from pathlib import Path

from .pick_deck import PickerReport


def write_picker_report(report: PickerReport, path: Path) -> None:
    """Write *report* as JSON to *path*, creating parent directories as needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "picks": [
            {
                "slide_index": p.slide_index,
                "layout": p.layout,
                "score": p.score,
                "runners_up": p.runners_up,
                "overrides_applied": p.overrides_applied,
            }
            for p in report.picks
        ],
        "arc_warnings": report.arc_warnings,
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
