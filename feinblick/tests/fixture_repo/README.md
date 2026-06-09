# fixture_repo — a tiny dirty repo for feinblick's integration test

A self-contained tree with KNOWN issues, exercised by
`tests/test_integration.py`. Nothing here shells out: the integration test
stubs the external engines (CytoScnPy / Tach / agnix) so CI needs no network,
while the **native** rules (skill validation + repo discipline) run for real
against this tree.

Planted issues:

| Path                                | Issue (rule)                                          |
| ----------------------------------- | ----------------------------------------------------- |
| `src/pkg/alpha.py`                  | unused `import os` + never-called `dead_alpha_function` (CytoScnPy, stubbed) |
| `skills/bad/SKILL.md`               | oversized body (PD), `name` != dir (FM004), weak description (DESC) |
| `skills/good/SKILL.md`              | clean control — must yield ZERO findings              |
| `feinschliff/examples/x/brief.txt`  | forbidden examples/ intermediate (FB-REPO-EX001)      |
| `feinblick.toml`                    | points code/skill roots at this fixture's own dirs    |
