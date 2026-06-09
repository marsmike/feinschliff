from pathlib import Path

from feinblick.model import Category, Severity
from feinblick.rules.repo_discipline import check_repo_discipline


def _mk(tmp_path, rel):
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x")
    return p


def test_allowed_files_pass(tmp_path):
    for rel in [
        "feinschliff/examples/a/README.md",
        "feinschliff/examples/a/deck.pdf",
        "feinschliff/examples/a/deck.pptx",
        "feinschliff/examples/a/slide.png",
        "feinschliff/examples/refurbish/ATTRIBUTION.md",
    ]:
        _mk(tmp_path, rel)
    assert check_repo_discipline(tmp_path) == []


def test_forbidden_files_flagged(tmp_path):
    for rel in [
        "feinschliff/examples/a/brief.txt",
        "feinschliff/examples/a/plan.yaml",
        "feinschliff/examples/a/chart.svg",
        "feinschliff/examples/a/d.exc.dsl",
    ]:
        _mk(tmp_path, rel)
    fs = check_repo_discipline(tmp_path)
    assert len(fs) == 4
    assert all(
        f.category == Category.REPO_DISCIPLINE and f.severity == Severity.ERROR for f in fs
    )
    assert {Path(f.location.path).name for f in fs} == {
        "brief.txt",
        "plan.yaml",
        "chart.svg",
        "d.exc.dsl",
    }


def test_no_examples_dir_is_noop(tmp_path):
    assert check_repo_discipline(tmp_path) == []
