"""Tests for ``skillgen.emit`` — the shipped agent-skill + slash commands.

The emitted ``SKILL.md`` must *dogfood* feinblick's own native skill rules:
it has to pass :func:`feinblick.rules.skills.check_skills` with no frontmatter,
description, or progressive-disclosure findings. Re-emitting must be byte for
byte identical (the templates are static, not timestamped).
"""

from __future__ import annotations

from pathlib import Path

from feinblick import skillgen
from feinblick.config import load_config
from feinblick.model import Category
from feinblick.rules.skills import check_skills


def test_emit_writes_the_four_files(tmp_path):
    written = skillgen.emit(tmp_path)
    skill_md = tmp_path / "skills" / "feinblick" / "SKILL.md"
    commands = [tmp_path / "commands" / f"{name}.md" for name in ("audit", "check", "health")]

    assert skill_md.is_file()
    for cmd in commands:
        assert cmd.is_file()

    written_set = {Path(p).resolve() for p in written}
    expected = {skill_md.resolve(), *(c.resolve() for c in commands)}
    assert written_set == expected
    assert len(written) == 4


def test_emitted_skill_passes_native_rules(tmp_path):
    skillgen.emit(tmp_path)
    cfg = load_config(tmp_path)
    findings = check_skills(tmp_path, ["skills"], cfg)

    bad = [
        f
        for f in findings
        if f.category
        in (
            Category.FRONTMATTER,
            Category.DESCRIPTION,
            Category.PROGRESSIVE_DISCLOSURE,
        )
    ]
    assert bad == [], f"shipped SKILL.md tripped its own rules: {[f.rule_id for f in bad]}"


def test_reemit_is_byte_identical(tmp_path):
    skillgen.emit(tmp_path)
    skill_md = tmp_path / "skills" / "feinblick" / "SKILL.md"
    commands = [tmp_path / "commands" / f"{name}.md" for name in ("audit", "check", "health")]
    first = {p: p.read_bytes() for p in (skill_md, *commands)}

    skillgen.emit(tmp_path)
    for path, content in first.items():
        assert path.read_bytes() == content


def test_command_files_mirror_feinbild_format(tmp_path):
    skillgen.emit(tmp_path)
    for name in ("audit", "check", "health"):
        text = (tmp_path / "commands" / f"{name}.md").read_text(encoding="utf-8")
        assert text.startswith("---\n")
        assert f"name: {name}\n" in text
        assert "user_invocable: true\n" in text
        assert f"# /{name}\n" in text
        assert "```bash\n" in text
        assert "feinblick " in text


def test_skill_body_is_command_first_and_under_budget(tmp_path):
    skillgen.emit(tmp_path)
    text = (tmp_path / "skills" / "feinblick" / "SKILL.md").read_text(encoding="utf-8")
    assert text.count("feinblick audit") >= 1
    assert "feinblick check" in text
    assert "feinblick health" in text
    # whole file (frontmatter + body) well under the 50-line ceiling
    assert len(text.splitlines()) <= 50
