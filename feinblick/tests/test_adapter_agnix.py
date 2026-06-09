from pathlib import Path

from feinblick.adapters.agnix import AgnixEngine, category_for_rule
from feinblick.adapters.base import Targets
from feinblick.model import Category, Domain, Severity
from feinblick.runner import RawOutput, Runner

FIX = Path(__file__).parent / "fixtures" / "agnix"


def _targets(tmp_path):
    from feinblick.config import load_config

    return Targets(
        repo_root=tmp_path, roots=["plugins"], test_globs=[], config=load_config(tmp_path)
    )


def test_rule_prefix_to_category():
    assert category_for_rule("AS-004") == Category.FRONTMATTER
    assert category_for_rule("AS-008") == Category.DESCRIPTION
    assert category_for_rule("AS-012") == Category.PROGRESSIVE_DISCLOSURE
    assert category_for_rule("CC-MEM-005") == Category.DESCRIPTION
    assert category_for_rule("CC-MEM-014") == Category.PROGRESSIVE_DISCLOSURE
    assert category_for_rule("CC-HK-009") == Category.HOOK
    assert category_for_rule("MCP-017") == Category.MCP


def test_parse_json_envelope(tmp_path):
    raw = RawOutput((FIX / "out-validate.json").read_text(), "", 1)
    fs = AgnixEngine().parse(raw, _targets(tmp_path))
    assert len(fs) == 5 and all(
        f.domain == Domain.SKILL and f.source_engine == "agnix" for f in fs
    )
    by_rule = {f.rule_id: f for f in fs}
    assert by_rule["CC-HK-009"].severity == Severity.ERROR  # from level
    assert by_rule["AS-012"].category == Category.PROGRESSIVE_DISCLOSURE
    assert by_rule["AS-004"].location.path == "feinbild/skills/svg/SKILL.md"


def test_parse_carries_location_and_suggestion(tmp_path):
    raw = RawOutput((FIX / "out-validate.json").read_text(), "", 1)
    fs = AgnixEngine().parse(raw, _targets(tmp_path))
    by_rule = {f.rule_id: f for f in fs}
    hk = by_rule["CC-HK-009"]
    assert hk.location.path == ".claude/settings.json"
    assert hk.location.line == 8 and hk.location.col == 3
    assert hk.evidence and "explicit confirmation" in hk.evidence
    assert hk.actions and hk.actions[0].auto_fixable is False
    assert hk.actions[0].description == hk.evidence


def test_parse_blank_stdout_yields_no_findings(tmp_path):
    assert AgnixEngine().parse(RawOutput("", "", 0), _targets(tmp_path)) == []
    assert AgnixEngine().parse(RawOutput("   \n", "", 0), _targets(tmp_path)) == []


def test_unavailable_when_npx_missing(tmp_path, monkeypatch):
    r = Runner(repo_root=tmp_path, cache=False)
    monkeypatch.setattr(r, "tool_available", lambda n: False)
    ok, reason = AgnixEngine().ensure_available(r, "latest")
    assert ok is False and "npx" in reason.lower()


def test_available_when_npx_present(tmp_path, monkeypatch):
    r = Runner(repo_root=tmp_path, cache=False)
    monkeypatch.setattr(r, "tool_available", lambda n: True)
    ok, reason = AgnixEngine().ensure_available(r, "latest")
    assert ok is True
