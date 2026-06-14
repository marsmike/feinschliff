"""Prose-content assertions for the deck skill's SKILL.md and reference files.

These tests are cheap (<1 s total, no LLM, no network) and exist to catch
regressions where the skill prose stops mentioning required pipeline artifacts
or loses the imperative framing that drives orchestrator behaviour.
"""
from __future__ import annotations

import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SKILLS_ROOT = Path(__file__).parent.parent / "skills" / "deck"
_SKILL_MD = _SKILLS_ROOT / "SKILL.md"
_PIPELINE_MD = _SKILLS_ROOT / "references" / "pipeline.md"
_MODES_MD = _SKILLS_ROOT / "references" / "modes.md"
_ITER_MD = _SKILLS_ROOT / "references" / "iteration-loop.md"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Layer 1 tests
# ---------------------------------------------------------------------------

def test_skill_lists_all_required_artifacts() -> None:
    """SKILL.md Pipeline section must mention every required pipeline artifact."""
    body = _read(_SKILL_MD)
    required = [
        "deck_brief.yaml",
        "commitment.yaml",
        "content_plan.json",
        "ghost_deck_report.md",
        "title_lint_report.md",
        "picker_report.json",
        "plan.yaml",
        "craft_report.md",
        "verify_report.md",
    ]
    missing = [a for a in required if a not in body]
    assert not missing, (
        f"SKILL.md is missing required artifact references: {missing}\n"
        "Add them to the Artifacts (all required) line in the Pipeline section."
    )


def test_pipeline_md_has_imperative_steps() -> None:
    """pipeline.md Step 0a, 0b, and 1a sections must contain imperative language."""
    body = _read(_PIPELINE_MD)
    imperatives = {"MUST", "Block until", "Required artifact", "Run"}

    # Split into sections by heading; heading pattern: "## Step <digit><optional letter>"
    heading_re = re.compile(r"^## Step \d[a-z]?", re.MULTILINE)
    positions = [(m.start(), m.group()) for m in heading_re.finditer(body)]

    # Build a map: heading text → section body
    sections: dict[str, str] = {}
    for i, (start, heading) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(body)
        sections[heading] = body[start:end]

    target_headings = {"## Step 0a", "## Step 0b", "## Step 1a"}
    for target in target_headings:
        matched = next(
            (text for h, text in sections.items() if h.startswith(target)), None
        )
        assert matched is not None, (
            f"pipeline.md: could not find section starting with '{target}'"
        )
        found = any(imp in matched for imp in imperatives)
        assert found, (
            f"pipeline.md section '{target}' contains none of {imperatives!r}.\n"
            "Add imperative language (MUST / Block until / Required artifact / Run)."
        )


def test_pipeline_md_no_perfection_bar() -> None:
    """deck/ skill files must not contain 'perfection bar' or iteration-count phrasing."""
    # Plain strings are checked as substrings (case-insensitive).
    # Patterns prefixed with "re:" are matched as regexes.
    # Note: "2–3 iterations" (a typical-range description) is allowed; we only
    # block bare "3 iterations" or "6 iterations" used as a hard target.
    forbidden = [
        "perfection bar",
        "perfectionist",
        # Match "3 iterations" NOT preceded by a digit or dash (avoids "2-3 iterations")
        r"re:(?<![0-9\-–])3 iterations",
        r"re:(?<![0-9\-–])6 iterations",
        "How perfect",
    ]
    offenders: list[str] = []
    for md_file in _SKILLS_ROOT.rglob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        for phrase in forbidden:
            if phrase.startswith("re:"):
                if re.search(phrase[3:], text, re.IGNORECASE):
                    offenders.append(f"{md_file.name}: '{phrase[3:]}'")
            elif phrase.lower() in text.lower():
                offenders.append(f"{md_file.name}: '{phrase}'")
    assert not offenders, (
        "Forbidden phrasing found under feinschliff/skills/deck/:\n"
        + "\n".join(f"  {o}" for o in offenders)
    )


def test_pipeline_md_fanout_is_default() -> None:
    """Step 2a and Step 4a must frame fan-out as the default, not an option."""
    body = _read(_PIPELINE_MD)

    # Locate Step 2a section
    m2a = re.search(r"^## Step 2a", body, re.MULTILINE)
    assert m2a, "pipeline.md: '## Step 2a' heading not found"
    # Locate Step 4a section
    m4a = re.search(r"^## Step 4a", body, re.MULTILINE)
    assert m4a, "pipeline.md: '## Step 4a' heading not found"

    soft_phrase = "Use this when"

    for label, match in (("Step 2a", m2a), ("Step 4a", m4a)):
        # Extract from this heading to the next ## heading
        rest = body[match.start():]
        next_heading = re.search(r"\n## ", rest[3:])
        section = rest[: next_heading.start() + 3] if next_heading else rest

        has_default = (
            "Default for slide_count" in section or "MUST fan out" in section
        )
        assert has_default, (
            f"pipeline.md {label}: expected 'Default for slide_count' or "
            f"'MUST fan out' but found neither.\n"
            "Fan-out must be framed as the default, not an optional path."
        )
        assert soft_phrase not in section, (
            f"pipeline.md {label}: soft phrasing '{soft_phrase}' must not appear; "
            "fan-out is mandatory, not conditional."
        )


def test_modes_md_create_lists_new_artifacts() -> None:
    """modes.md 'create' section must mention at least 3 of the 4 new artifacts."""
    body = _read(_MODES_MD)

    # Find the create section: from "## create" to the next ## heading
    m = re.search(r"^## create", body, re.MULTILINE)
    assert m, "modes.md: '## create' heading not found"
    rest = body[m.start():]
    next_h = re.search(r"\n## ", rest[3:])
    create_section = rest[: next_h.start() + 3] if next_h else rest

    required = [
        "deck_brief.yaml",
        "commitment.yaml",
        "ghost_deck_report.md",
        "picker_report.json",
    ]
    found = [a for a in required if a in create_section]
    assert len(found) >= 3, (
        f"modes.md create section mentions only {found} of {required}.\n"
        "At least 3 of the 4 new artifacts must appear in the create outputs list."
    )


def test_iteration_loop_references_8_cap() -> None:
    """iteration-loop.md must explicitly state the 8-iteration safety cap."""
    body = _read(_ITER_MD)
    # Accept "8-iteration safety cap", "8 iterations (hard safety cap)",
    # "8-iteration hard stop", etc.
    patterns = [
        r"8.iteration safety cap",
        r"8.iteration hard stop",
        r"8 iterations.*safety cap",
        r"safety cap.*8",
        r"hard stop.*8",
        r"8.*safety cap",
    ]
    matched = any(re.search(p, body, re.IGNORECASE) for p in patterns)
    assert matched, (
        "iteration-loop.md: could not find '8-iteration safety cap' or equivalent.\n"
        "The file must state the hard cap of 8 iterations near the word 'safety cap'."
    )


def test_skill_md_body_under_40_lines() -> None:
    """SKILL.md body (excluding frontmatter) must be ≤ 40 lines."""
    text = _read(_SKILL_MD)
    # Strip YAML frontmatter block: lines between the two '---' markers
    if text.startswith("---"):
        end_marker = text.index("---", 3)
        body = text[end_marker + 3:].lstrip("\n")
    else:
        body = text

    lines = body.splitlines()
    assert len(lines) <= 40, (
        f"SKILL.md body is {len(lines)} lines (limit: 40). "
        "Trim the skill body; move detail into references/."
    )
