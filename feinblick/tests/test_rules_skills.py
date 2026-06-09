from pathlib import Path

from feinblick.model import Category, Domain, Severity
from feinblick.rules.skills import check_skills


def _skill(root: Path, name: str, desc: str, body_lines: int = 10, dirname=None):
    d = root / (dirname or name)
    d.mkdir(parents=True)
    body = "\n".join(f"line {i}" for i in range(body_lines))
    (d / "SKILL.md").write_text(f"---\nname: {name}\ndescription: {desc}\n---\n# {name}\n{body}\n")
    return d


def _cfg(tmp_path, max_lines=500):
    from feinblick.config import load_config

    cfg = load_config(tmp_path)
    cfg.skills.skill_md_max_lines = max_lines  # dataclasses are non-frozen
    return cfg


def test_good_skill_has_no_findings(tmp_path):
    root = tmp_path / "skills"
    _skill(root, "svg", "Generate SVG diagrams from a DSL. Use for charts and flows.")
    fs = check_skills(tmp_path, ["skills"], _cfg(tmp_path))
    assert fs == []


def test_oversized_body_flagged(tmp_path):
    root = tmp_path / "skills"
    _skill(root, "big", "Generate things. Use when you need big output here.", body_lines=20)
    fs = check_skills(tmp_path, ["skills"], _cfg(tmp_path, max_lines=10))
    assert any(
        f.category == Category.PROGRESSIVE_DISCLOSURE and f.severity == Severity.WARNING
        for f in fs
    )


def test_bad_name_and_dir_mismatch(tmp_path):
    root = tmp_path / "skills"
    _skill(
        root, "Bad_Name", "Generate. Use when needed for the thing here now.", dirname="something"
    )
    fs = check_skills(tmp_path, ["skills"], _cfg(tmp_path))
    cats = {f.rule_id for f in fs if f.category == Category.FRONTMATTER}
    assert any(r.startswith("FB-SK-FM") for r in cats)


def test_weak_description_flagged(tmp_path):
    root = tmp_path / "skills"
    _skill(root, "weak", "Does stuff")  # too short, no trigger clause
    fs = check_skills(tmp_path, ["skills"], _cfg(tmp_path))
    assert any(f.category == Category.DESCRIPTION for f in fs)


def test_unreadable_skill_md_degrades_to_finding(tmp_path):
    # One non-UTF-8 SKILL.md must surface as a finding, not crash the pipeline.
    d = tmp_path / "skills" / "broken"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_bytes(b"\xff\xfe\x00broken")
    fs = check_skills(tmp_path, ["skills"], _cfg(tmp_path))
    assert any(
        f.rule_id == "FB-SK-READ001" and f.severity == Severity.ERROR for f in fs
    )


def test_all_findings_are_skill_domain_from_rules_engine(tmp_path):
    root = tmp_path / "skills"
    _skill(root, "Bad_Name", "Does stuff", dirname="something")
    fs = check_skills(tmp_path, ["skills"], _cfg(tmp_path))
    assert fs
    assert all(f.domain == Domain.SKILL and f.source_engine == "feinblick:rules" for f in fs)
