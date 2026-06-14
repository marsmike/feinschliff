"""OVERBUDGET pre-gate: bound slot text exceeding the layout's front-matter
`chars` budget warns at bind time. Advisory only — the authoritative check
is the textfit overflow gate."""
from pathlib import Path

from feinschliff.deck.content_metadata import warn_overbudget_slots

_LAYOUT = """\
---
role: content
ideal_count: [1, 3]
data_band: none
comparison: false
slots:
  text_1: {role: title, chars: 40, default: Title}
  text_2: {role: body, chars: 200, default: Body}
---
canvas 1920x1080
text 100,100 maxwidth:900 maxheight:80 "{{ text_1 | default(\\"Title\\") }}"
text 100,300 maxwidth:900 maxheight:400 "{{ text_2 | default(\\"Body\\") }}"
"""


def _layout(tmp_path: Path) -> Path:
    p = tmp_path / "content.slide.dsl"
    p.write_text(_LAYOUT, encoding="utf-8")
    return p


def test_overbudget_warns(tmp_path, capsys):
    warn_overbudget_slots(
        {"text_1": "x" * 95, "text_2": "fine"},
        layout_path=_layout(tmp_path), slide_index=3,
    )
    err = capsys.readouterr().err
    assert "OVERBUDGET" in err and "slot=text_1" in err
    assert "bound=95" in err and "budget=40" in err and "text_2" not in err


def test_within_budget_silent(tmp_path, capsys):
    warn_overbudget_slots(
        {"text_1": "Short title"}, layout_path=_layout(tmp_path), slide_index=1,
    )
    assert "OVERBUDGET" not in capsys.readouterr().err


def test_no_profile_no_crash(tmp_path, capsys):
    p = tmp_path / "bare.slide.dsl"
    p.write_text('canvas 1920x1080\ntext 0,0 maxwidth:100 "{{ t }}"\n', encoding="utf-8")
    warn_overbudget_slots({"t": "x" * 500}, layout_path=p, slide_index=1)
    assert "OVERBUDGET" not in capsys.readouterr().err
