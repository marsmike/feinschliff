"""Finding dedupe + severity reconciliation.

Multiple engines (and the native checks) can independently report the *same*
underlying problem — e.g. cytoscnpy and ruff both flagging the same unused
function. They share a symbol-anchored :pyattr:`Finding.fingerprint`, so we
collapse them into a single Finding:

* **severity** — reconciled to the highest of the group (max by
  :pyattr:`Severity.rank`); a problem two engines disagree on is as bad as its
  worst reporter says.
* **source_engine** — merged into a stable, comma-joined string in first-seen
  order (``"cytoscnpy,ruff"``) so the reader sees who corroborated it.
* **actions** — unioned, dropping byte-identical duplicates while keeping the
  first-seen order (so the same remediation isn't listed twice).

Group order is **stable**: each fingerprint's first appearance fixes its slot
in the output. The representative kept is the first finding of the group, with
its severity / source_engine / actions overwritten by the reconciled values.
"""

from __future__ import annotations

from dataclasses import replace

from feinblick.model import Action, Finding


def dedupe(findings: list[Finding]) -> list[Finding]:
    """Collapse findings sharing a ``fingerprint`` into one reconciled Finding.

    Highest severity wins; ``source_engine`` becomes a comma-joined string;
    ``actions`` are unioned (identical ones dropped). Stable first-seen order.
    """
    groups: dict[str, list[Finding]] = {}
    order: list[str] = []
    for f in findings:
        fp = f.fingerprint
        if fp not in groups:
            groups[fp] = []
            order.append(fp)
        groups[fp].append(f)

    out: list[Finding] = []
    for fp in order:
        group = groups[fp]
        if len(group) == 1:
            out.append(group[0])
            continue
        out.append(_reconcile(group))
    return out


def _reconcile(group: list[Finding]) -> Finding:
    """Merge a fingerprint group into a single representative Finding."""
    base = group[0]
    severity = max((f.severity for f in group), key=lambda s: s.rank)

    engines: list[str] = []
    for f in group:
        if f.source_engine not in engines:
            engines.append(f.source_engine)

    actions: list[Action] = []
    seen: set[tuple] = set()
    for f in group:
        for action in f.actions:
            key = (action.description, action.auto_fixable, action.engine_fix_cmd)
            if key in seen:
                continue
            seen.add(key)
            actions.append(action)

    return replace(
        base,
        severity=severity,
        source_engine=",".join(engines),
        actions=actions,
    )
