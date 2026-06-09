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


class _ArgvCapture:
    """Stub runner: records the argv that run() builds; returns empty output."""

    def __init__(self):
        self.argv = None

    def uvx(self, pkg, version, args):
        return ["uvx", f"{pkg}@{version}", *args]

    def run_raw(self, argv, cache_key=None, inputs=None, cwd=None):
        self.argv = argv
        return RawOutput("{}", "", 0)


def test_run_excludes_concrete_test_folders_not_glob_stars(tmp_path):
    # '**/tests/**' names the folder 'tests'; '**/test_*.py' is a file pattern
    # and names no folder. A literal '**' must never reach --exclude-folders.
    from feinblick.config import load_config

    t = Targets(
        repo_root=tmp_path, roots=["sample"],
        test_globs=["**/tests/**", "**/test_*.py"], config=load_config(tmp_path),
    )
    r = _ArgvCapture()
    CytoScnPyEngine().run(r, t, "1.2.23")
    argv = r.argv
    excluded = [argv[i + 1] for i, a in enumerate(argv) if a == "--exclude-folders"]
    assert excluded == ["tests"]
    assert "**" not in argv


def test_dead_code_actions_are_honest(tmp_path):
    # Removal is manual (the engine can't apply it); the whitelist command is a
    # *suppression*, offered as a runnable command with the real roots inlined.
    fs = _parse("out-deadcode.json", tmp_path)
    f = next(f for f in fs if f.category == Category.DEAD_CODE)
    remove, suppress = f.actions
    assert remove.auto_fixable is False and remove.engine_fix_cmd is None
    assert suppress.auto_fixable is True
    assert "<roots>" not in (suppress.engine_fix_cmd or "")
    assert "sample" in suppress.engine_fix_cmd  # the actual scan root
    assert "--make-whitelist" in suppress.engine_fix_cmd


def test_is_error_distinguishes_failure_from_findings_present():
    eng = CytoScnPyEngine()
    # findings-present run: exit 1 BUT valid JSON -> not an error
    assert eng.is_error(RawOutput('{"schema_version":"2"}', "", 1)) is None
    # missing path: exit 1, empty stdout -> error
    assert eng.is_error(RawOutput("", "", 1)) is not None
    # crash with a message on stderr surfaces that message
    err = eng.is_error(RawOutput("", "boom: no such path", 1))
    assert err is not None and "boom" in err
    # non-JSON stdout -> error
    assert eng.is_error(RawOutput("Traceback...", "", 1)) is not None
