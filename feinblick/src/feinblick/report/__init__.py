"""Reporters — render a finding set in one of four formats.

Every reporter exposes ``render(findings, verdict, health, meta) -> str``.
``REPORTERS`` maps a format name to its callable; ``render(fmt, ...)`` dispatches.
"""
from __future__ import annotations

from feinblick.model import Finding
from feinblick.report import json, markdown, sarif, terminal

REPORTERS = {
    "terminal": terminal.render,
    "json": json.render,
    "sarif": sarif.render,
    "markdown": markdown.render,
}


def render(
    fmt: str,
    findings: list[Finding],
    verdict: str,
    health: dict,
    meta: dict,
) -> str:
    """Dispatch to the named reporter. Raise ``ValueError`` on an unknown format."""
    try:
        reporter = REPORTERS[fmt]
    except KeyError:
        raise ValueError(
            f"unknown report format: {fmt!r} (known: {', '.join(sorted(REPORTERS))})"
        ) from None
    return reporter(findings, verdict, health, meta)


__all__ = ["REPORTERS", "render"]
