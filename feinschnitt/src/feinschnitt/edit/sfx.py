"""SFX cue derivation — the plan IS the cue sheet.

Cues come from the aligned beats + caption chunks, never hand-authored:
whoosh on the hook, a pop on every takeover entrance, a write-stroke on each
caption-emphasis moment — except the LAST emphasis cue (closers want
silence). Assets are user-supplied; missing files skip their cues with a
warning (no bundled audio)."""
from __future__ import annotations

import os
from pathlib import Path

from feinschnitt.edit.lint import OVERLAY_KINDS

SFX_DIR_ENV = "FEINSCHNITT_SFX_DIR"
DEFAULT_SFX_DIR = Path.home() / ".local" / "share" / "feinschnitt" / "sfx"
CUE_KINDS = ("whoosh", "pop", "stroke")


def sfx_dir() -> Path:
    env = os.environ.get(SFX_DIR_ENV)
    return Path(env) if env else DEFAULT_SFX_DIR


def resolve_assets(directory: Path | None = None) -> dict[str, Path]:
    """cue kind -> audio file. First match by stem name wins (whoosh.*)."""
    d = directory or sfx_dir()
    found: dict[str, Path] = {}
    if not d.is_dir():
        return found
    for f in sorted(d.iterdir()):
        if f.is_file() and f.stem in CUE_KINDS and f.stem not in found:
            found[f.stem] = f
    return found


def derive_cues(beats: list[dict], captions: list[dict]) -> list[dict]:
    """[{kind, at}] in absolute seconds, sorted. Pure plan-derived."""
    cues: list[dict] = []
    takeovers = [b for b in beats
                 if b.get("kind") not in OVERLAY_KINDS
                 and isinstance(b.get("start_sec"), (int, float))
                 and not isinstance(b.get("start_sec"), bool)]
    hooks = [b for b in beats if b.get("kind") == "hook_title"
             and isinstance(b.get("start_sec"), (int, float))
             and not isinstance(b.get("start_sec"), bool)]
    if hooks:
        # time-earliest hook, not list-first — lint doesn't enforce beat order
        first_hook = min(hooks, key=lambda b: float(b["start_sec"]))
        cues.append({"kind": "whoosh", "at": float(first_hook["start_sec"])})
    for b in takeovers:
        cues.append({"kind": "pop", "at": float(b["start_sec"])})
    emphasis_starts = []
    for chunk in captions:
        if any(w.get("accent") for w in chunk.get("words", [])):
            emphasis_starts.append(float(chunk["s"]))
    for at in emphasis_starts[:-1]:  # last emphasis cue suppressed
        cues.append({"kind": "stroke", "at": at})
    return sorted(cues, key=lambda c: c["at"])


def plan_cues(beats: list[dict], captions: list[dict],
              directory: Path | None = None
              ) -> tuple[list[dict], list[str]]:
    """Resolved cues [{kind, at, path}] + warnings for unresolvable kinds."""
    assets = resolve_assets(directory)
    cues, warnings, missing = [], [], set()
    for cue in derive_cues(beats, captions):
        path = assets.get(cue["kind"])
        if path is None:
            missing.add(cue["kind"])
            continue
        cues.append({**cue, "path": str(path)})
    for kind in sorted(missing):
        warnings.append(f"sfx: no '{kind}.*' file in {directory or sfx_dir()} "
                        "— cues of this kind skipped")
    return cues, warnings
