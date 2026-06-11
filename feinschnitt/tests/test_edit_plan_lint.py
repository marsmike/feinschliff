"""Plan loading + lint contracts."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from feinschnitt.edit import EditError, plan as planmod  # noqa: E402


def _write(tmp_path, payload):
    p = tmp_path / "edit_plan.json"
    p.write_text(json.dumps(payload))
    return p


def test_load_plan_ok(tmp_path):
    p = _write(tmp_path, {"video": "clip.mp4", "beats": [
        {"kind": "stat_punch", "start_sec": 1.6, "end_sec": 4.0,
         "value": "10×", "caption": "faster", "reason": "hero number"}]})
    loaded = planmod.load_plan(p)
    assert loaded["beats"][0]["kind"] == "stat_punch"


def test_load_plan_rejects_garbage(tmp_path):
    p = tmp_path / "edit_plan.json"
    p.write_text("not json")
    with pytest.raises(EditError):
        planmod.load_plan(p)


def test_load_plan_requires_beats_list(tmp_path):
    p = _write(tmp_path, {"video": "clip.mp4"})
    with pytest.raises(EditError):
        planmod.load_plan(p)
