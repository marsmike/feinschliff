from pathlib import Path

from feinblick.adapters.base import Targets
from feinblick.adapters.cytoscnpy import CytoScnPyEngine
from feinblick.model import Category, Domain, Severity
from feinblick.runner import RawOutput

FIX = Path(__file__).parent / "fixtures" / "cytoscnpy"


def _targets(tmp_path):
    from feinblick.config import load_config

    return Targets(
        repo_root=tmp_path, roots=["sample"], test_globs=[], config=load_config(tmp_path)
    )


def _parse(name, tmp_path):
    raw = RawOutput((FIX / name).read_text(), "", 1)  # exit 1 with JSON = findings present
    return CytoScnPyEngine().parse(raw, _targets(tmp_path))


def test_parses_dead_code(tmp_path):
    fs = _parse("out-deadcode.json", tmp_path)
    dead = [f for f in fs if f.category == Category.DEAD_CODE]
    assert dead and all(
        f.domain == Domain.CODE and f.source_engine == "cytoscnpy" for f in dead
    )
    f = next(f for f in dead if "dead_alpha_function" in (f.location.symbol or ""))
    assert f.location.symbol == "alpha.dead_alpha_function"  # synthesized from `name`
    assert f.severity in (Severity.WARNING, Severity.INFO)  # synthesized (json has none)
    assert f.rule_id and f.rule_id.startswith("CSP-")  # synthesized


def test_parses_and_dedupes_clones(tmp_path):
    fs = _parse("out-clones.json", tmp_path)
    clones = [f for f in fs if f.category == Category.DUPLICATION]
    # each clone pair appears twice in raw JSON (is_duplicate true/false) -> one Finding per pair
    assert clones and len(clones) == len(
        {tuple(sorted([f.location.path, (f.evidence or "")])) for f in clones}
    )
    assert all(f.rule_id == "CSP-C100" for f in clones)


def test_parses_quality_complexity_and_secrets(tmp_path):
    fs = _parse("out-full-scan.json", tmp_path)
    assert any(f.category == Category.COMPLEXITY for f in fs)  # CSP-Q301/Q302/Q304 -> Complexity
    # secrets/danger are out of v1 quality focus: assert they are NOT emitted as findings
    assert all(f.rule_id is None or not f.rule_id.startswith("CSP-S") for f in fs)
