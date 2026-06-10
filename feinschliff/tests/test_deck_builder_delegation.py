"""The advanced deck subcommands delegate to the feinschliff-builder CLI when
the builder package is not importable in this venv (the per-plugin launcher
model), per the family's "capability call, never import" coupling rule.
"""
from __future__ import annotations

import builtins

import pytest

from feinschliff.cli import deck


def _hide_builder(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "feinschliff_builder" or name.startswith("feinschliff_builder."):
            raise ImportError("no feinschliff_builder in office venv")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)


def test_inline_when_builder_importable(monkeypatch):
    # Builder is importable in the dev/test venv → no delegation, no exit.
    called = {}
    monkeypatch.setattr("os.execv", lambda *a: called.setdefault("execv", a))
    deck._require_or_delegate_builder("deck storyline")
    assert "execv" not in called


def test_delegates_to_builder_cli_when_present(monkeypatch):
    _hide_builder(monkeypatch)
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/feinschliff-builder")
    monkeypatch.setattr("sys.argv", ["feinschliff", "deck", "storyline", "plan.yaml"])
    captured = {}
    monkeypatch.setattr("os.execv", lambda path, argv: captured.update(path=path, argv=argv))
    deck._require_or_delegate_builder("deck storyline")
    assert captured["path"] == "/usr/bin/feinschliff-builder"
    assert captured["argv"] == ["/usr/bin/feinschliff-builder", "deck", "storyline", "plan.yaml"]


def test_exits_2_when_builder_absent(monkeypatch):
    _hide_builder(monkeypatch)
    monkeypatch.setattr("shutil.which", lambda name: None)
    with pytest.raises(SystemExit) as exc:
        deck._require_or_delegate_builder("deck storyline")
    assert exc.value.code == 2
