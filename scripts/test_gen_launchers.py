"""Unit tests for the manifest drift checks in gen_launchers.py.

Run from the repo root:
    python3 -m pytest scripts/test_gen_launchers.py -v

The check functions accept file CONTENTS as arguments, so these tests are
fully offline and require no filesystem access.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Make the sibling script importable without installing it as a package.
sys.path.insert(0, str(Path(__file__).parent))
from gen_launchers import (  # noqa: E402
    _PLUGIN_NAMES,
    _WS_MEMBERS,
    _CLI_NAMES,
    _parse_ci_yml,
    check_marketplace,
    check_pyproject_workspace,
    check_ci_yml,
)


# ---------------------------------------------------------------------------
# Fixtures — minimal valid content matching the live repo state
# ---------------------------------------------------------------------------

def _marketplace_text(plugins: list[dict] | None = None) -> str:
    """Build a valid marketplace.json string."""
    if plugins is None:
        plugins = [
            {"name": n, "source": f"./{n}"}
            for n in sorted(_PLUGIN_NAMES)
        ]
    return json.dumps({"plugins": plugins})


def _plugin_jsons_for(names: list[str]) -> dict[str, str]:
    """Build plugin.json stubs for the given names (dir = name, json name = name)."""
    return {n: json.dumps({"name": n}) for n in names}


def _pyproject_text(members: list[str] | None = None) -> str:
    if members is None:
        members = sorted(_WS_MEMBERS)
    joined = "\n".join(f'    "{m}",' for m in members)
    return f"[tool.uv.workspace]\nmembers = [\n{joined}\n]\n"


# Minimal ci.yml text mirroring the structural anchors that _parse_ci_yml expects.
_DEDICATED = {"feinschliff", "feinschliff-builder"}
_PKG_MATRIX = sorted(_WS_MEMBERS - _DEDICATED)
_WHL_MATRIX = sorted(_CLI_NAMES)
_CLI_ALT    = "|".join(sorted(_CLI_NAMES))
_MEMBER_LIST = ", ".join(f'"{m}"' for m in sorted(_WS_MEMBERS))


def _ci_yml_text(
    members_list: str | None = None,
    cli_alt: str | None = None,
    pkg_matrix: str | None = None,
    whl_matrix: str | None = None,
) -> str:
    ml = members_list or _MEMBER_LIST
    ca = cli_alt or _CLI_ALT
    pm = pkg_matrix or ", ".join(_PKG_MATRIX)
    wm = whl_matrix or ", ".join(_WHL_MATRIX)
    return f"""\
      - name: All workspace packages share one version
        run: |
          python3 - <<'PY'
          members = [{ml}]
          PY
      - name: Skill docs use bare CLIs
        run: |
          grep -rn -E 'uv run ({ca})\\b' */skills/
    packages:
      strategy:
        matrix:
          pkg: [{pm}]
    wheel-install:
      strategy:
        matrix:
          plugin: [{wm}]
"""


# ---------------------------------------------------------------------------
# check_marketplace
# ---------------------------------------------------------------------------

class TestCheckMarketplace:
    def test_valid_passes(self):
        pj = _plugin_jsons_for(list(_PLUGIN_NAMES))
        errors = check_marketplace(_marketplace_text(), pj)
        assert errors == []

    def test_missing_plugin_detected(self):
        # Remove one plugin from marketplace listing
        plugins = [
            {"name": n, "source": f"./{n}"}
            for n in sorted(_PLUGIN_NAMES)
            if n != "feinschliff-extra"
        ]
        pj = _plugin_jsons_for(list(_PLUGIN_NAMES))
        errors = check_marketplace(_marketplace_text(plugins), pj)
        assert any("feinschliff-extra" in e for e in errors), errors

    def test_extra_plugin_detected(self):
        plugins = [
            {"name": n, "source": f"./{n}"}
            for n in sorted(_PLUGIN_NAMES)
        ] + [{"name": "phantom-plugin", "source": "./phantom-plugin"}]
        pj = _plugin_jsons_for(list(_PLUGIN_NAMES) + ["phantom-plugin"])
        errors = check_marketplace(_marketplace_text(plugins), pj)
        assert any("phantom-plugin" in e for e in errors), errors

    def test_plugin_json_name_mismatch_detected(self):
        pj = _plugin_jsons_for(list(_PLUGIN_NAMES))
        # Corrupt one plugin.json so its name field doesn't match the marketplace entry
        pj["feinschliff"] = json.dumps({"name": "WRONG"})
        errors = check_marketplace(_marketplace_text(), pj)
        assert any("feinschliff" in e and "WRONG" in e for e in errors), errors

    def test_missing_plugin_json_detected(self):
        pj = {n: json.dumps({"name": n}) for n in _PLUGIN_NAMES if n != "feinbild"}
        errors = check_marketplace(_marketplace_text(), pj)
        assert any("feinbild" in e for e in errors), errors

    def test_bad_json_returns_error(self):
        errors = check_marketplace("{not valid json", {})
        assert any("JSON parse error" in e for e in errors), errors


# ---------------------------------------------------------------------------
# check_pyproject_workspace
# ---------------------------------------------------------------------------

class TestCheckPyprojectWorkspace:
    def test_valid_passes(self):
        errors = check_pyproject_workspace(_pyproject_text())
        assert errors == []

    def test_missing_member_detected(self):
        members = [m for m in sorted(_WS_MEMBERS) if m != "feinschmiede"]
        errors = check_pyproject_workspace(_pyproject_text(members))
        assert any("feinschmiede" in e for e in errors), errors

    def test_extra_member_detected(self):
        members = sorted(_WS_MEMBERS) + ["feinschliff-extra"]
        errors = check_pyproject_workspace(_pyproject_text(members))
        assert any("feinschliff-extra" in e for e in errors), errors

    def test_bad_toml_returns_error(self):
        errors = check_pyproject_workspace("[invalid toml\n")
        assert any("TOML parse error" in e for e in errors), errors


# ---------------------------------------------------------------------------
# _parse_ci_yml and check_ci_yml
# ---------------------------------------------------------------------------

class TestParseCiYml:
    def test_parses_all_lists(self):
        result = _parse_ci_yml(_ci_yml_text())
        assert result["members_heredoc"] == _WS_MEMBERS
        assert result["cli_regex"] == _CLI_NAMES
        assert result["packages_matrix"] == _WS_MEMBERS - _DEDICATED
        assert result["wheel_matrix"] == _CLI_NAMES

    def test_empty_on_missing_anchors(self):
        result = _parse_ci_yml("# nothing here\n")
        assert result["members_heredoc"] == set()
        assert result["cli_regex"] == set()
        assert result["packages_matrix"] == set()
        assert result["wheel_matrix"] == set()


class TestCheckCiYml:
    def test_valid_passes(self):
        errors = check_ci_yml(_ci_yml_text())
        assert errors == []

    def test_missing_member_in_heredoc_detected(self):
        members = ", ".join(f'"{m}"' for m in sorted(_WS_MEMBERS) if m != "feinschnitt")
        errors = check_ci_yml(_ci_yml_text(members_list=members))
        assert any("feinschnitt" in e for e in errors), errors

    def test_extra_member_in_heredoc_detected(self):
        members = ", ".join(f'"{m}"' for m in sorted(_WS_MEMBERS)) + ', "feinschliff-extra"'
        errors = check_ci_yml(_ci_yml_text(members_list=members))
        assert any("feinschliff-extra" in e for e in errors), errors

    def test_missing_cli_in_regex_detected(self):
        alt = "|".join(n for n in sorted(_CLI_NAMES) if n != "feinklang")
        errors = check_ci_yml(_ci_yml_text(cli_alt=alt))
        assert any("feinklang" in e for e in errors), errors

    def test_extra_cli_in_regex_detected(self):
        alt = "|".join(sorted(_CLI_NAMES)) + "|phantom"
        errors = check_ci_yml(_ci_yml_text(cli_alt=alt))
        assert any("phantom" in e for e in errors), errors

    def test_packages_matrix_missing_entry_detected(self):
        pm = ", ".join(n for n in _PKG_MATRIX if n != "feinschmiede")
        errors = check_ci_yml(_ci_yml_text(pkg_matrix=pm))
        assert any("feinschmiede" in e for e in errors), errors

    def test_wheel_matrix_missing_entry_detected(self):
        wm = ", ".join(n for n in _WHL_MATRIX if n != "feinbild")
        errors = check_ci_yml(_ci_yml_text(whl_matrix=wm))
        assert any("feinbild" in e for e in errors), errors
