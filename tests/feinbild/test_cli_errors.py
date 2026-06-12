"""Bad input must produce a clean `Error:` message + exit 1 — never a traceback,
and never leak the optional-Playwright import error for a missing file.
"""

from feinbild import cli


def test_typo_color_token_clean_error(capsys, tmp_path):
    src = tmp_path / "x.exc.dsl"
    src.write_text('canvas 200x100\nbox a 10,10 80x40 "A" fill:primry\n')
    rc = cli.main(["excalidraw", "expand", str(src), "-o", str(tmp_path / "o.excalidraw")])
    err = capsys.readouterr().err
    assert rc == 1
    assert "Error:" in err
    assert "Traceback" not in err
    assert "did you mean" in err  # helpful suggestion preserved


def test_unknown_brand_clean_error(capsys, tmp_path):
    src = tmp_path / "x.svg.dsl"
    src.write_text("canvas 200x100\nrect a 10,10 80x40 primary\n")
    rc = cli.main(["svg", "expand", str(src), "--brand", "doesnotexist", "-o", str(tmp_path / "o.svg")])
    err = capsys.readouterr().err
    assert rc == 1
    assert "Error:" in err
    assert "Traceback" not in err


def test_missing_input_file_clean_error(capsys, tmp_path):
    rc = cli.main(["svg", "expand", str(tmp_path / "nope.svg.dsl"), "-o", str(tmp_path / "o.svg")])
    err = capsys.readouterr().err
    assert rc == 1
    assert "Error:" in err
    assert "Traceback" not in err


def test_missing_render_input_no_playwright_leak(capsys, tmp_path):
    rc = cli.main(["svg", "render", str(tmp_path / "nope.svg"), "-o", str(tmp_path / "o.png")])
    err = capsys.readouterr().err
    assert rc == 1
    assert "Error:" in err
    assert "not found" in err
    assert "playwright" not in err.lower()  # the confusing fallback error must not surface
