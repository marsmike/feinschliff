"""Native skill checks over every ``SKILL.md`` under the configured roots.

These run *natively* (no agnix required) so feinblick's skill verdicts stay
consistent whether or not the agnix adapter executed. Three families of checks,
deliberately mirroring agnix rule codes:

* **Progressive-disclosure budget** (≈AS-012/CC-MEM-014): body line count over
  ``config.skills.skill_md_max_lines`` -> :data:`Category.PROGRESSIVE_DISCLOSURE`
  warning ``FB-SK-PD001``.
* **Frontmatter** (≈AS-001..006/017): a ``---``-delimited block with ``name`` and
  ``description``; ``name`` slug-shaped and equal to the parent directory name ->
  :data:`Category.FRONTMATTER` errors ``FB-SK-FM001..004``.
* **Description trigger quality** (≈AS-008/009 + the feinschliff "Use when…"
  convention): description present, >= 40 chars, free of ``<...>`` angle
  brackets, and carrying a ``Use when|for|to`` trigger clause ->
  :data:`Category.DESCRIPTION` warnings ``FB-SK-DESC001..003``.

The frontmatter parser is a tiny stdlib affair (no pyyaml): the leading
``---`` block's ``key: value`` lines, split on the first colon.
"""

from __future__ import annotations

import re
from pathlib import Path

from feinblick.model import Action, Category, Domain, Finding, Location, Severity

_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_ANGLE_RE = re.compile(r"<[^>]*>")
_TRIGGER_RE = re.compile(r"\b[Uu]se (when|for|to)\b")
_DESC_MIN_LEN = 40

_SOURCE = "feinblick:rules"


def _parse_frontmatter(text: str) -> tuple[dict[str, str], int]:
    """Return ``(meta, body_line_count)`` for a SKILL.md ``text``.

    ``meta`` is the parsed leading ``---`` frontmatter block (empty when absent).
    ``body_line_count`` counts the lines after the closing ``---`` (the whole
    file when there is no frontmatter).
    """
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        meta: dict[str, str] = {}
        body_start = len(lines)
        for idx in range(1, len(lines)):
            if lines[idx].strip() == "---":
                body_start = idx + 1
                break
            if ":" in lines[idx]:
                key, _, value = lines[idx].partition(":")
                meta[key.strip()] = value.strip()
        body = lines[body_start:]
        return meta, len(body)
    return {}, len(lines)


def _location(skill_md: Path, repo_root: Path) -> Location:
    try:
        rel = skill_md.relative_to(repo_root).as_posix()
    except ValueError:
        rel = skill_md.as_posix()
    return Location(path=rel)


def _finding(
    category: Category,
    severity: Severity,
    location: Location,
    message: str,
    rule_id: str,
    evidence: str | None = None,
    actions: list[Action] | None = None,
) -> Finding:
    return Finding(
        domain=Domain.SKILL,
        category=category,
        severity=severity,
        location=location,
        message=message,
        source_engine=_SOURCE,
        rule_id=rule_id,
        evidence=evidence,
        actions=actions or [],
    )


def _check_progressive_disclosure(
    body_lines: int, budget: int, location: Location
) -> list[Finding]:
    if budget and body_lines > budget:
        return [
            _finding(
                Category.PROGRESSIVE_DISCLOSURE,
                Severity.WARNING,
                location,
                f"SKILL.md body is {body_lines} lines, over the {budget}-line "
                "progressive-disclosure budget",
                "FB-SK-PD001",
                evidence=f"{body_lines} lines > {budget}",
                actions=[
                    Action(
                        "Move detail into linked references and keep SKILL.md lean",
                        auto_fixable=False,
                    )
                ],
            )
        ]
    return []


def _check_frontmatter(
    meta: dict[str, str], skill_md: Path, location: Location
) -> list[Finding]:
    findings: list[Finding] = []
    name = meta.get("name")
    description = meta.get("description")

    if not name:
        findings.append(
            _finding(
                Category.FRONTMATTER,
                Severity.ERROR,
                location,
                "SKILL.md frontmatter is missing a 'name' field",
                "FB-SK-FM001",
            )
        )
    if not description:
        findings.append(
            _finding(
                Category.FRONTMATTER,
                Severity.ERROR,
                location,
                "SKILL.md frontmatter is missing a 'description' field",
                "FB-SK-FM002",
            )
        )
    if name and not _NAME_RE.match(name):
        findings.append(
            _finding(
                Category.FRONTMATTER,
                Severity.ERROR,
                location,
                f"Skill name {name!r} must be a lowercase slug "
                "(^[a-z0-9]+(-[a-z0-9]+)*$)",
                "FB-SK-FM003",
                evidence=name,
            )
        )
    parent = skill_md.parent.name
    if name and name != parent:
        findings.append(
            _finding(
                Category.FRONTMATTER,
                Severity.ERROR,
                location,
                f"Skill name {name!r} does not match its directory {parent!r}",
                "FB-SK-FM004",
                evidence=f"name={name} dir={parent}",
            )
        )
    return findings


def _check_description(description: str | None, location: Location) -> list[Finding]:
    findings: list[Finding] = []
    if not description:
        # Absence is already reported by the frontmatter check (FM002).
        return findings
    if len(description) < _DESC_MIN_LEN:
        findings.append(
            _finding(
                Category.DESCRIPTION,
                Severity.WARNING,
                location,
                f"Skill description is too short ({len(description)} chars); "
                f"aim for >= {_DESC_MIN_LEN} characters",
                "FB-SK-DESC001",
                evidence=f"{len(description)} chars < {_DESC_MIN_LEN}",
            )
        )
    if _ANGLE_RE.search(description):
        findings.append(
            _finding(
                Category.DESCRIPTION,
                Severity.WARNING,
                location,
                "Skill description contains <...> angle brackets; use plain prose",
                "FB-SK-DESC002",
            )
        )
    if not _TRIGGER_RE.search(description):
        findings.append(
            _finding(
                Category.DESCRIPTION,
                Severity.WARNING,
                location,
                "Skill description lacks a trigger clause "
                "(e.g. 'Use when ...', 'Use for ...', 'Use to ...')",
                "FB-SK-DESC003",
            )
        )
    return findings


def check_skills(repo_root: Path, roots: list[str], config: object) -> list[Finding]:
    """Run the native skill checks over every ``SKILL.md`` under ``roots``."""
    repo_root = Path(repo_root)
    budget = config.skills.skill_md_max_lines
    findings: list[Finding] = []
    seen: set[Path] = set()

    for root in roots:
        root_dir = repo_root / root
        if not root_dir.is_dir():
            continue
        for skill_md in sorted(root_dir.glob("**/SKILL.md")):
            resolved = skill_md.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            text = skill_md.read_text(encoding="utf-8")
            meta, body_lines = _parse_frontmatter(text)
            location = _location(skill_md, repo_root)

            findings.extend(_check_progressive_disclosure(body_lines, budget, location))
            findings.extend(_check_frontmatter(meta, skill_md, location))
            findings.extend(_check_description(meta.get("description"), location))

    return findings
