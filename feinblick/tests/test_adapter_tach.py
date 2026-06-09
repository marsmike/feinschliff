from pathlib import Path

from feinblick.adapters.base import Targets
from feinblick.adapters.tach import TachEngine, scaffold_tach_toml
from feinblick.model import Category, Domain, Severity
from feinblick.runner import RawOutput

FIX = Path(__file__).parent / "fixtures" / "tach"


def _targets(tmp_path):
    from feinblick.config import load_config

    return Targets(
        repo_root=tmp_path,
        roots=["feinschliff/lib"],
        test_globs=[],
        config=load_config(tmp_path),
    )


def test_parses_boundary_array(tmp_path):
    raw = RawOutput((FIX / "out-check-nodeps.json").read_text(), "", 1)
    fs = TachEngine().parse(raw, _targets(tmp_path))
    bnd = [f for f in fs if f.category == Category.BOUNDARY]
    assert len(bnd) == 3
    f = bnd[0]
    assert f.location.path == "mod_a/__init__.py" and f.location.line == 2
    assert f.severity == Severity.ERROR
    assert "cannot depend on" in f.message.lower()  # synthesized message
    assert f.domain == Domain.CODE and f.source_engine == "tach"
    assert f.rule_id == "TACH-UndeclaredDependency"
    assert f.location.symbol == "mod_b.helper_b"


def test_parses_circular_object(tmp_path):
    raw = RawOutput((FIX / "out-check-cycle-on.json").read_text(), "", 1)
    fs = TachEngine().parse(raw, _targets(tmp_path))
    circ = [f for f in fs if f.category == Category.CIRCULAR_DEP]
    assert len(circ) == 1 and "mod_a" in circ[0].message and "mod_b" in circ[0].message
    assert circ[0].severity == Severity.ERROR
    assert circ[0].rule_id == "TACH-CYCLE"
    assert circ[0].location.path == "feinschliff/lib"
    assert circ[0].source_engine == "tach"


def test_clean_run_yields_no_findings(tmp_path):
    raw = RawOutput("[]", "", 0)
    assert TachEngine().parse(raw, _targets(tmp_path)) == []


def test_config_error_on_stderr_is_not_findings(tmp_path):
    raw = RawOutput("", (FIX / "out-check-noconfig.txt").read_text(), 1)
    assert TachEngine().parse(raw, _targets(tmp_path)) == []  # empty stdout -> no findings


def test_scaffold_tach_toml_from_roots(tmp_path):
    toml = scaffold_tach_toml(roots=["feinschliff/lib", "feinbild/src"])
    assert "source_roots" in toml and "forbid_circular_dependencies = true" in toml
    assert "[[modules]]" in toml


def test_engine_registered():
    from feinblick.adapters import tach

    assert tach.ENGINE.name == "tach"
