"""Tests for `feinschliff brand inspect` — focus on the inheritance line."""
from __future__ import annotations

import json


from feinschliff_builder.cli.main import main


def test_inspect_prints_inheritance_chain_for_extending_brand(capsys):
    """feinschliff-dark extends feinschliff → inheritance line shows the chain."""
    rc = main(["brand", "inspect", "feinschliff-dark"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "inheritance:" in out
    # Parent-most → child rendering.
    assert "feinschliff → feinschliff-dark" in out


def test_inspect_omits_inheritance_line_for_brand_without_extends(capsys):
    """A brand whose DESIGN.md has no `extends:` doesn't print the line."""
    rc = main(["brand", "inspect", "feinschliff"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "inheritance:" not in out


def test_inspect_no_design_md_skips_inheritance_gracefully(tmp_path, monkeypatch, capsys):
    """When DESIGN.md is missing, inspect skips the inheritance line without error."""
    bundled = tmp_path / "bundled" / "brands"
    d = bundled / "orphan"
    d.mkdir(parents=True)
    # tokens.json present, but no DESIGN.md → inheritance walk must not crash.
    (d / "tokens.json").write_text(json.dumps({
        "color": {"accent": {"$value": "#000000"}},
        "font-family": {},
        "font-size": {},
    }))
    monkeypatch.setenv("FEINSCHLIFF_BRAND_PATH", "")
    monkeypatch.setattr("feinschmiede.brand_discovery._bundled_brands_root", lambda: bundled)
    monkeypatch.setattr("feinschmiede.brand_discovery._user_brands_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr("feinschmiede.brand_discovery._plugin_brands_roots", lambda: [])
    monkeypatch.setattr("feinschmiede.brand_discovery._cwd_dev_brands_roots", lambda: [])

    rc = main(["brand", "inspect", "orphan"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "inheritance:" not in out
