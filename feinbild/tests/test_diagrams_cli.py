from pathlib import Path

from feinbild import diagrams_cli

OTA = """canvas 1720x480
text title 100,40 "How a Device Gets Updated" size:title
ellipse cloud 80,180 280x160 "Cloud" fill:start
box check    480,180 280x160 "Device\\nChecks" fill:primary
box install  880,180 280x160 "Device\\nInstalls" fill:secondary
box restart  1280,180 320x160 "Device\\nRestarts" fill:end
arrow cloud -> check    label:"sends update"
arrow check -> install  label:"OK"
arrow install -> restart label:"safely"
"""


def test_excalidraw_expand_then_render(tmp_path: Path):
    src = tmp_path / "ota.exc.dsl"
    src.write_text(OTA)
    exc = tmp_path / "ota.excalidraw"
    png = tmp_path / "ota.png"
    assert diagrams_cli.cmd_excalidraw_expand(src, exc, brand="feinschliff") == 0
    assert exc.read_text().startswith("{")  # Excalidraw JSON
    assert diagrams_cli.cmd_render(exc, png) == 0
    assert png.stat().st_size > 200  # real PNG bytes
