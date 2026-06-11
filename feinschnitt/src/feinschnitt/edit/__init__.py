"""Pre-recorded footage edit pipeline — plan-driven Remotion engine.

The agent authors edit_plan.json (data, never code); deterministic stages
(transcribe / lint / align / render / verify) enforce taste rules cheaply
before any expensive render. See skills/edit/SKILL.md.
"""


class EditError(Exception):
    """Expected edit-pipeline failure — surfaces as a clean CLI error."""
