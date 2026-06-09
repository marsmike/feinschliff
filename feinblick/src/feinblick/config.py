"""feinblick.toml loading + baked feinschliff defaults.

Zero-config first run uses the feinschliff monorepo defaults baked in below.
An optional ``feinblick.toml`` at the repo root deep-merges over them. Engine
names are validated against ``KNOWN_ENGINES``; pinned versions resolve through
``engine_version`` (override or :data:`DEFAULT_VERSIONS`).

The cfg dataclasses are intentionally *mutable* (non-frozen) so callers and
tests can override individual fields (e.g. ``cfg.skills.skill_md_max_lines``)
without rebuilding the whole tree.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_VERSIONS: dict[str, str] = {
    "cytoscnpy": "1.2.23",
    "tach": "0.35.0",
    "agnix": "latest",
}

KNOWN_ENGINES: set[str] = {"cytoscnpy", "tach", "agnix"}


@dataclass
class CodeCfg:
    roots: list[str] = field(default_factory=lambda: ["feinschliff/lib"])
    test_globs: list[str] = field(default_factory=lambda: ["**/tests/**", "**/test_*.py"])
    engines: list[str] = field(default_factory=lambda: ["cytoscnpy", "tach"])


@dataclass
class SkillsCfg:
    roots: list[str] = field(default_factory=lambda: ["."])
    # Symmetric with CodeCfg so the orchestrator can build Targets uniformly for
    # either domain; skills have no test dirs to exclude, hence empty by default.
    test_globs: list[str] = field(default_factory=list)
    engines: list[str] = field(default_factory=lambda: ["agnix"])
    skill_md_max_lines: int = 500


@dataclass
class GateCfg:
    fail_on: list[str] = field(default_factory=lambda: ["error"])
    warn_on: list[str] = field(default_factory=lambda: ["warning"])
    baseline: Path = field(default_factory=lambda: Path(".feinblick/baseline.json"))
    tolerance: int = 0


@dataclass
class Config:
    repo_root: Path
    code: CodeCfg = field(default_factory=CodeCfg)
    skills: SkillsCfg = field(default_factory=SkillsCfg)
    gate: GateCfg = field(default_factory=GateCfg)
    engine_versions: dict[str, str] = field(default_factory=dict)

    def engine_version(self, name: str) -> str:
        """Resolve the pinned version for ``name`` (override or baked default)."""
        return self.engine_versions.get(name, DEFAULT_VERSIONS[name])


def _validate_engines(names: list[str]) -> None:
    for name in names:
        if name not in KNOWN_ENGINES:
            raise ValueError(f"unknown engine: {name!r} (known: {sorted(KNOWN_ENGINES)})")


def load_config(repo_root: Path) -> Config:
    """Load ``repo_root/feinblick.toml`` (if present) over baked defaults."""
    repo_root = Path(repo_root)
    cfg = Config(repo_root=repo_root)

    toml_path = repo_root / "feinblick.toml"
    if toml_path.is_file():
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
        _merge_section(cfg.code, data.get("code", {}))
        _merge_section(cfg.skills, data.get("skills", {}))
        _merge_gate(cfg.gate, data.get("gate", {}))
        for name, sub in (data.get("engines", {}) or {}).items():
            version = sub.get("version") if isinstance(sub, dict) else None
            if version is not None:
                cfg.engine_versions[name] = version

    _validate_engines(cfg.code.engines)
    _validate_engines(cfg.skills.engines)
    return cfg


def _merge_section(target: object, overrides: dict) -> None:
    for key, value in overrides.items():
        if hasattr(target, key):
            setattr(target, key, value)


def _merge_gate(target: GateCfg, overrides: dict) -> None:
    for key, value in overrides.items():
        if key == "baseline":
            target.baseline = Path(value)
        elif hasattr(target, key):
            setattr(target, key, value)
