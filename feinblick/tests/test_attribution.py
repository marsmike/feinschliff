import subprocess

from feinblick import attribution
from feinblick.model import Category, Domain, Finding, Location, Severity


def _finding(path: str) -> Finding:
    return Finding(
        domain=Domain.CODE,
        category=Category.DEAD_CODE,
        severity=Severity.WARNING,
        location=Location(path=path, line=11, symbol="x"),
        message="msg",
        source_engine="cytoscnpy",
        rule_id="CSP-U001",
    )


def _git(repo, *args):
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(repo):
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "commit.gpgsign", "false")


def test_changed_paths_includes_modified_tracked_file(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    f = repo / "lib" / "a.py"
    f.parent.mkdir(parents=True)
    f.write_text("print(1)\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "initial")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    # modify the tracked file (uncommitted working-tree change)
    f.write_text("print(2)\n")

    changed = attribution.changed_paths(repo, base)
    assert "lib/a.py" in changed


def test_changed_paths_includes_staged_and_committed(tmp_path):
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "base.py").write_text("x = 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "initial")
    base = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    # a committed-after-base change
    (repo / "committed.py").write_text("y = 2\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "second")

    # a staged-but-uncommitted change
    (repo / "staged.py").write_text("z = 3\n")
    _git(repo, "add", "staged.py")

    changed = attribution.changed_paths(repo, base)
    assert "committed.py" in changed
    assert "staged.py" in changed


def test_attribute_filters_findings_by_changed_path():
    findings = [_finding("lib/a.py"), _finding("lib/b.py"), _finding("lib/c.py")]
    kept = attribution.attribute(findings, {"lib/a.py", "lib/c.py"})
    assert [f.location.path for f in kept] == ["lib/a.py", "lib/c.py"]


def test_attribute_empty_changed_set_keeps_nothing():
    findings = [_finding("lib/a.py")]
    assert attribution.attribute(findings, set()) == []


def test_parse_diff_file_extracts_plus_plus_plus_paths(tmp_path):
    diff = (
        "diff --git a/lib/a.py b/lib/a.py\n"
        "index 0000000..1111111 100644\n"
        "--- a/lib/a.py\n"
        "+++ b/lib/a.py\n"
        "@@ -1 +1 @@\n"
        "-print(1)\n"
        "+print(2)\n"
        "diff --git a/lib/new.py b/lib/new.py\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/lib/new.py\n"
        "@@ -0,0 +1 @@\n"
        "+x = 1\n"
    )
    p = tmp_path / "changes.diff"
    p.write_text(diff)
    paths = attribution.parse_diff_file(p)
    assert paths == {"lib/a.py", "lib/new.py"}


def test_parse_diff_file_ignores_dev_null_target(tmp_path):
    # a pure deletion has '+++ /dev/null' which must not be captured.
    diff = (
        "diff --git a/lib/gone.py b/lib/gone.py\n"
        "deleted file mode 100644\n"
        "--- a/lib/gone.py\n"
        "+++ /dev/null\n"
        "@@ -1 +0,0 @@\n"
        "-print(1)\n"
    )
    p = tmp_path / "del.diff"
    p.write_text(diff)
    assert attribution.parse_diff_file(p) == set()
