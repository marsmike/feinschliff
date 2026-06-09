"""The pipeline — pool engine findings, run native rules, gate, verdict.

:func:`run_pipeline` is the single orchestration entry the CLI drives. It walks
the requested ``domains``, asks each configured engine to ``ensure_available``
-> ``run`` -> ``parse`` (recording any unavailable engine in ``meta`` and, under
``strict``, aborting), pools the findings through :func:`run_rules` (native
checks + dedupe + health), then — when gating is requested — classifies against
the baseline, optionally attributes to changed code, and computes a verdict.

The result is a :class:`Result` carrying the deduped findings, the health dict,
the verdict (``pass`` / ``warn`` / ``fail``), the baseline-introduced set, and a
``meta`` dict describing which engines ran, which were unavailable, the scanned
domains, and how many candidates drove the verdict.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from feinblick import baseline
from feinblick.adapters import ENGINES
from feinblick.adapters.base import Targets
from feinblick.attribution import attribute, changed_paths, parse_diff_file
from feinblick.config import Config
from feinblick.model import Finding
from feinblick.rules import run_rules
from feinblick.runner import Runner


class OrchestrationError(RuntimeError):
    """A tooling failure that aborts the run under ``--strict``.

    Raised when an engine is unavailable or errors and the caller asked for
    strict mode. The CLI catches this and exits with a distinct non-findings
    code rather than crashing with a traceback.
    """


@dataclass
class Result:
    findings: list[Finding]
    health: dict
    verdict: str
    introduced: list[Finding]
    meta: dict


def run_pipeline(
    repo_root: Path,
    config: Config,
    *,
    domains,
    runner: Runner,
    gate: str | None = None,
    since_ref: str | None = None,
    diff_file: str | None = None,
    strict: bool = False,
) -> Result:
    """Run the engine -> rules -> gate pipeline and return a :class:`Result`.

    ``domains`` selects which config sections (``"code"`` / ``"skills"``) supply
    engines + roots and which native checks run. ``gate`` is ``None``
    (informational, always ``pass``), ``"all"`` (gate the full deduped set), or
    ``"introduced"`` (gate only findings attributed to changed code via
    ``since_ref`` / ``diff_file``). ``strict`` turns an unavailable engine into a
    :class:`RuntimeError` instead of a recorded-and-skipped degradation.
    """
    repo_root = Path(repo_root)
    findings: list[Finding] = []
    meta: dict = {
        "engines": [],
        "unavailable": [],
        "errors": [],
        "missing_roots": [],
        "domains": sorted(domains),
    }

    for domain in domains:
        section = getattr(config, domain)
        # Drop configured roots that don't exist so a stale config can never
        # silently "scan nothing" and report a misleading clean run.
        existing_roots = [r for r in section.roots if (repo_root / r).exists()]
        for r in section.roots:
            if r not in existing_roots:
                meta["missing_roots"].append(f"{domain}:{r}")
        if not existing_roots:
            continue
        for engine_name in section.engines:
            eng = ENGINES.get(engine_name)
            if eng is None:
                continue
            version = config.engine_version(engine_name)
            targets = Targets(repo_root, existing_roots, section.test_globs, config)
            # "Not applicable to this repo" (e.g. tach without a tach.toml) is a
            # documented degradation with guidance — recorded as unavailable but
            # never escalated by strict, which is about tooling failures only.
            applicable_check = getattr(eng, "is_applicable", None)
            if callable(applicable_check):
                applicable, why = applicable_check(targets)
                if not applicable:
                    meta["unavailable"].append({"engine": engine_name, "reason": why})
                    continue
            ok, reason = eng.ensure_available(runner, targets, version)
            if not ok:
                meta["unavailable"].append({"engine": engine_name, "reason": reason})
                if strict:
                    raise OrchestrationError(reason)
                continue
            raw = eng.run(runner, targets, version)
            # An engine that errored at runtime (crash / missing path / unparseable
            # output) must not masquerade as a clean run — record and degrade.
            err_check = getattr(eng, "is_error", None)
            err = err_check(raw) if callable(err_check) else None
            if err is not None:
                meta["errors"].append({"engine": engine_name, "reason": err})
                if strict:
                    raise OrchestrationError(f"{engine_name}: {err}")
                continue
            findings += eng.parse(raw, targets)
            meta["engines"].append(engine_name)

    merged, health = run_rules(findings, repo_root, config, domains)

    baseline_path = config.gate.baseline
    if not baseline_path.is_absolute():
        baseline_path = repo_root / baseline_path
    accepted = baseline.load(baseline_path)
    introduced, _ = baseline.classify(merged, accepted)

    candidates = _gate_candidates(
        gate, merged, introduced, repo_root, since_ref, diff_file
    )

    # A `--gate introduced` run with no diff source attributes nothing, so the
    # verdict is a vacuous PASS — flag it so a forgotten --changed-since isn't
    # misread as "tree is clean".
    if gate == "introduced" and not (since_ref or diff_file):
        meta["gate_note"] = (
            "gate=introduced but no --changed-since/--diff-file given — nothing was "
            "attributed; this verdict does not reflect overall tree health "
            f"({len(merged)} findings exist; use --gate all or pass a diff ref)"
        )

    verdict = _verdict(gate, candidates, config)
    meta["introduced"] = len(candidates)

    return Result(merged, health, verdict, introduced, meta)


def _gate_candidates(
    gate: str | None,
    merged: list[Finding],
    introduced: list[Finding],
    repo_root: Path,
    since_ref: str | None,
    diff_file: str | None,
) -> list[Finding]:
    if gate == "all":
        return merged
    if gate == "introduced":
        candidates = introduced
        if since_ref:
            return attribute(candidates, changed_paths(repo_root, since_ref))
        if diff_file:
            return attribute(candidates, parse_diff_file(diff_file))
        return []
    return []


def _verdict(gate: str | None, candidates: list[Finding], config: Config) -> str:
    if gate is None:
        return "pass"
    fail_on = set(config.gate.fail_on)
    warn_on = set(config.gate.warn_on)
    fails = [c for c in candidates if c.severity.value in fail_on]
    warns = [c for c in candidates if c.severity.value in warn_on]
    if len(fails) > config.gate.tolerance:
        return "fail"
    return "warn" if warns else "pass"


__all__ = ["OrchestrationError", "Result", "run_pipeline"]
