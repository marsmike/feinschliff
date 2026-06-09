"""`feinbild verify` — structural lint of a rendered diagram via the shared engine validator."""

import json

from feinbild import cli

_GOOD = {
    "type": "excalidraw", "version": 2, "appState": {},
    "elements": [
        {"id": "a", "type": "rectangle", "x": 0, "y": 0, "width": 300, "height": 120},
        {"id": "t", "type": "text", "containerId": "a", "text": "OK",
         "fontSize": 16, "x": 10, "y": 40, "width": 280, "height": 40},
    ],
}
_OVERFLOW = {
    "type": "excalidraw", "version": 2, "appState": {},
    "elements": [
        {"id": "a", "type": "rectangle", "x": 0, "y": 0, "width": 80, "height": 40},
        {"id": "t", "type": "text", "containerId": "a",
         "text": "a very long label that absolutely overflows this tiny container box",
         "fontSize": 24, "x": 0, "y": 0, "width": 80, "height": 40},
    ],
}


def test_verify_clean_passes(capsys, tmp_path):
    p = tmp_path / "ok.excalidraw"
    p.write_text(json.dumps(_GOOD))
    rc = cli.main(["verify", str(p)])
    assert rc == 0
    assert "no structural defects" in capsys.readouterr().out


def test_verify_overflow_fails(capsys, tmp_path):
    p = tmp_path / "bad.excalidraw"
    p.write_text(json.dumps(_OVERFLOW))
    rc = cli.main(["verify", str(p)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "diagram-overflow" in err


def test_verify_malformed_file_fails(capsys, tmp_path):
    p = tmp_path / "broken.excalidraw"
    p.write_text("{not valid json")
    rc = cli.main(["verify", str(p)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "invalid" in err.lower()
