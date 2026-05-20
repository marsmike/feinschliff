"""CI gate: every feinschliff skill must pass `claude-skills-cli validate` with 0 errors and 0 warnings."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

FEINSCHLIFF_ROOT = Path(__file__).parent.parent
SKILLS = ["deck"]  # compile and improve-brand moved to feinschliff-builder


@pytest.mark.parametrize("skill_name", SKILLS)
def test_skill_is_validator_clean(skill_name: str) -> None:
    result = subprocess.run(
        ["npx", "-y", "claude-skills-cli", "validate", f"skills/{skill_name}"],
        cwd=FEINSCHLIFF_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"Validator failed for skills/{skill_name}:\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )
    warning_lines = [line for line in result.stdout.splitlines() if line.lstrip().startswith("⚠️")]
    assert not warning_lines, (
        f"Validator warnings for skills/{skill_name}:\n" + "\n".join(warning_lines)
    )
