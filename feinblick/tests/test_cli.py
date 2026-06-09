"""Tests for the feinblick CLI.

All engine work is monkeypatched out (a fake ``run_pipeline`` or an empty
``ENGINES`` registry) so nothing shells to ``uvx``/``npx`` or the network.
"""

from __future__ import annotations

import json

import pytest

from feinblick import cli
from feinblick.model import Action, Category, Domain, Finding, Location, Severity
from feinblick.orchestrator import Result


def _finding():
    return Finding(
        domain=Domain.CODE, category=Category.DEAD_CODE, severity=Severity.WARNING,
        location=Location(path="lib/a.py", line=11, symbol="a.dead"),
        message="'a.dead' is dead", source_engine="cytoscnpy", rule_id="CSP-U001",
        evidence="confidence=high",
        actions=[Action(description="Remove it", auto_fixable=True)],
    )


def _meta(domains=(), introduced=0):
    return {"engines": [], "unavailable": [], "domains": list(domains),
            "introduced": introduced}


def _empty_engines(monkeypatch):
    import feinblick.adapters as adapters
    import feinblick.orchestrator as orch
    monkeypatch.setattr(adapters, "ENGINES", {})
    monkeypatch.setattr(orch, "ENGINES", {}, raising=False)


def test_version(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    assert "feinblick" in capsys.readouterr().out


def test_no_subcommand_prints_help(capsys):
    assert cli.main([]) == 0
    out = capsys.readouterr().out
    assert "audit" in out and "check" in out


def test_strict_tooling_error_exits_cleanly(tmp_path, monkeypatch, capsys):
    # --strict + an OrchestrationError must be a clean exit 2, NOT a traceback.
    from feinblick.orchestrator import OrchestrationError
    monkeypatch.chdir(tmp_path)

    def boom(*a, **k):
        raise OrchestrationError("agnix unavailable")

    monkeypatch.setattr(cli, "run_pipeline", boom)
    rc = cli.main(["check", "skills", "--strict"])
    assert rc == 2
    assert "tooling error" in capsys.readouterr().err


def test_check_json_over_empty_tree(tmp_path, monkeypatch, capsys):
    _empty_engines(monkeypatch)
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["check", "all", "--format", "json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "findings" in payload and "verdict" in payload
    assert "health" in payload and "meta" in payload
    assert payload["verdict"] == "pass"  # no gate on check


def test_check_code_only(tmp_path, monkeypatch, capsys):
    _empty_engines(monkeypatch)
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["check", "code", "--format", "json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["meta"]["domains"] == ["code"]


def test_audit_pass_exit_zero(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    def fake_pipeline(repo_root, config, **kw):
        return Result(
            findings=[], health={"score": 100, "hotspots": []},
            verdict="pass", introduced=[],
            meta={"engines": [], "unavailable": [], "domains": ["code", "skills"],
                  "introduced": 0},
        )

    monkeypatch.setattr(cli, "run_pipeline", fake_pipeline)
    assert cli.main(["audit", "--format", "json"]) == 0


def test_audit_fail_exit_one(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def fake_pipeline(repo_root, config, **kw):
        return Result(findings=[_finding()], health={"score": 80, "hotspots": []},
                      verdict="fail", introduced=[_finding()],
                      meta={"engines": [], "unavailable": [], "domains": ["code", "skills"],
                            "introduced": 1})

    monkeypatch.setattr(cli, "run_pipeline", fake_pipeline)
    assert cli.main(["audit", "--format", "json"]) == 1


def test_audit_warn_exit_zero(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def fake_pipeline(repo_root, config, **kw):
        return Result(findings=[_finding()], health={"score": 90, "hotspots": []},
                      verdict="warn", introduced=[],
                      meta={"engines": [], "unavailable": [], "domains": ["code", "skills"],
                            "introduced": 0})

    monkeypatch.setattr(cli, "run_pipeline", fake_pipeline)
    assert cli.main(["audit", "--format", "json"]) == 0


def test_audit_passes_gate_and_attribution_args(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    seen = {}

    def fake_pipeline(repo_root, config, **kw):
        seen.update(kw)
        return Result([], {"score": 100, "hotspots": []}, "pass", [],
                      {"engines": [], "unavailable": [], "domains": [], "introduced": 0})

    monkeypatch.setattr(cli, "run_pipeline", fake_pipeline)
    cli.main(["audit", "--gate", "all", "--changed-since", "main", "--strict"])
    assert seen["gate"] == "all"
    assert seen["since_ref"] == "main"
    assert seen["strict"] is True
    assert seen["domains"] == {"code", "skills"}


def test_health_prints_score(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    def fake_pipeline(repo_root, config, **kw):
        return Result([], {"score": 73, "hotspots": [{"path": "lib/a.py", "findings": 3}]},
                      "pass", [], _meta())

    monkeypatch.setattr(cli, "run_pipeline", fake_pipeline)
    assert cli.main(["health"]) == 0
    out = capsys.readouterr().out
    assert "73" in out and "lib/a.py" in out


def test_init_writes_toml(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["init"])
    assert rc == 0
    cfg = tmp_path / "feinblick.toml"
    assert cfg.is_file()
    text = cfg.read_text()
    assert "[code]" in text and "[skills]" in text and "[gate]" in text
    # idempotent: a second init does not error and leaves content intact
    rc2 = cli.main(["init"])
    assert rc2 == 0
    assert cfg.read_text() == text


def test_init_idempotent_does_not_clobber(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    custom = "[code]\nroots = [\"custom\"]\n"
    (tmp_path / "feinblick.toml").write_text(custom)
    cli.main(["init"])
    assert (tmp_path / "feinblick.toml").read_text() == custom


def test_baseline_save_writes_fingerprints(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    def fake_pipeline(repo_root, config, **kw):
        return Result([_finding()], {"score": 90, "hotspots": []}, "pass", [],
                      {"engines": [], "unavailable": [], "domains": [], "introduced": 0})

    monkeypatch.setattr(cli, "run_pipeline", fake_pipeline)
    assert cli.main(["baseline", "save"]) == 0
    bl = tmp_path / ".feinblick" / "baseline.json"
    assert bl.is_file()
    data = json.loads(bl.read_text())
    assert data["fingerprints"] == [_finding().fingerprint]
    assert "1" in capsys.readouterr().out  # count printed


def test_audit_rejects_removed_baseline_flag(tmp_path, monkeypatch):
    # `audit --baseline` was an accepted-but-ignored flag; it must now be rejected.
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc:
        cli.main(["audit", "--baseline", "x.json"])
    assert exc.value.code == 2


def test_baseline_save_rejects_removed_gate_flag(tmp_path, monkeypatch):
    # `baseline save --gate` was never read by the handler; reject it.
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as exc:
        cli.main(["baseline", "save", "--gate", "all"])
    assert exc.value.code == 2


def test_skill_emit_without_out_requires_plugin_root(tmp_path, monkeypatch, capsys):
    # Installed in a venv the package's grandparent is NOT the plugin dir;
    # emitting there would scribble into the venv. Demand --out instead.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "_default_skill_out", lambda: None)
    assert cli.main(["skill", "emit"]) == 2
    assert "--out" in capsys.readouterr().err


def test_default_skill_out_is_the_plugin_root_in_dev_checkout():
    out = cli._default_skill_out()
    assert out is not None and (out / ".claude-plugin").is_dir()


def test_config_error_exits_cleanly(tmp_path, monkeypatch, capsys):
    # A typo'd engine name in feinblick.toml must be a clean exit 2 with the
    # known-engines hint — never a raw ValueError traceback.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "feinblick.toml").write_text('[code]\nengines = ["cytoscanpy"]\n')
    rc = cli.main(["check", "code"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "config error" in err and "cytoscanpy" in err


def test_malformed_toml_exits_cleanly(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "feinblick.toml").write_text("not toml [[[")
    rc = cli.main(["check", "code"])
    assert rc == 2
    assert "config error" in capsys.readouterr().err


def test_explain_finds_by_rule_id(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    def fake_pipeline(repo_root, config, **kw):
        return Result([_finding()], {"score": 90, "hotspots": []}, "pass", [],
                      {"engines": [], "unavailable": [], "domains": [], "introduced": 0})

    monkeypatch.setattr(cli, "run_pipeline", fake_pipeline)
    assert cli.main(["explain", "CSP-U001"]) == 0
    out = capsys.readouterr().out
    assert "is dead" in out and "Remove it" in out


def test_explain_finds_by_fingerprint(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    fp = _finding().fingerprint

    def fake_pipeline(repo_root, config, **kw):
        return Result([_finding()], {"score": 90, "hotspots": []}, "pass", [],
                      {"engines": [], "unavailable": [], "domains": [], "introduced": 0})

    monkeypatch.setattr(cli, "run_pipeline", fake_pipeline)
    assert cli.main(["explain", fp]) == 0
    assert "is dead" in capsys.readouterr().out


def test_explain_not_found(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    def fake_pipeline(repo_root, config, **kw):
        return Result([], {"score": 100, "hotspots": []}, "pass", [],
                      {"engines": [], "unavailable": [], "domains": [], "introduced": 0})

    monkeypatch.setattr(cli, "run_pipeline", fake_pipeline)
    assert cli.main(["explain", "NOPE-999"]) == 0
    assert "no finding" in capsys.readouterr().out.lower()


def test_repo_root_walks_up_to_git(tmp_path, monkeypatch, capsys):
    # repo_root resolution: a .git marker above cwd is found.
    (tmp_path / ".git").mkdir()
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    monkeypatch.chdir(sub)
    seen = {}

    def fake_pipeline(repo_root, config, **kw):
        seen["repo_root"] = repo_root
        return Result([], {"score": 100, "hotspots": []}, "pass", [],
                      {"engines": [], "unavailable": [], "domains": [], "introduced": 0})

    monkeypatch.setattr(cli, "run_pipeline", fake_pipeline)
    cli.main(["check", "--format", "json"])
    assert seen["repo_root"] == tmp_path
