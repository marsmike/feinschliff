#!/usr/bin/env python3
"""recorder — drive any CLI session in tmux+asciinema from a recipe.

Backs the ``feinschnitt record`` subcommand.

Usage
-----
    feinschnitt record recipes/foo.recipe.toml              # record + post-process
    feinschnitt record recipes/foo.recipe.toml --dry-run    # parse only, print steps
    feinschnitt record recipes/foo.recipe.toml --no-render  # skip agg/ffmpeg
    feinschnitt record recipes/foo.recipe.toml --keep       # keep tmux session after run

Inputs
------
    recipes/<name>.recipe.toml   — declarative description of the CLI session
                                   (see cli-recorder/schema/recipe.schema.json)

Outputs (under $CLAUDE_PROJECT_DIR/.recordings/<name>/ by default)
-----------------------------------------------------------------
    <name>.cast              — asciicast v3, post-processed
    <name>.scene-index.json  — step → time-window map (sidecar)
    <name>.gif               — rendered preview (if agg installed)
    <name>.mp4               — rendered preview (if ffmpeg installed)

How it works
------------
    1. Load the recipe, merge the named profile from cli-recorder/profiles/.
    2. Spawn a tmux session that runs `script -q /dev/null asciinema rec ...`
       wrapping the recipe's `command`. The `script` wrapper provides a PTY so
       asciinema's stdin forwarding works; without it, `tmux send-keys` never
       reaches the child process.
    3. For each step, dispatch on action:
         - type_prompt:    type text char-by-char, send Enter, optional dismiss
         - send_key:       send a single named tmux key
         - wait_for_pattern: block until regex matches the pane content
         - pause:          sleep
       Record (start_s, end_s) for each step into the scene index.
    4. Send /exit (or `exit`) and wait for asciinema to flush the cast.
    5. Post-process: strip cursor/NBSP artifacts, scale idle gaps by 1/N.
    6. Optionally render GIF (agg) and MP4 (ffmpeg).
    7. Write the scene-index.json sidecar.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib  # 3.11+
except ImportError:
    try:
        import tomli as tomllib  # 3.9–3.10
    except ImportError:
        sys.exit("error: tomllib not available — install tomli: `uv pip install tomli`")

# ── Constants ────────────────────────────────────────────────────────────────

CLAUDE_BIN = shutil.which("claude") or "/Users/mike/.local/bin/claude"
IDLE_POLL_INTERVAL = 0.4
IDLE_TIMEOUT_SECS  = 120

def _recorder_home() -> Path:
    """Locate skills/cli-recorder/ (which holds profiles/ + schema/).

    The launcher exports FEINSCHNITT_RECORDER_HOME; fall back to the repo
    layout (feinschnitt/src/feinschnitt/recorder.py -> feinschnitt/skills/cli-recorder)
    for dev/test runs without the launcher.
    """
    env = os.environ.get("FEINSCHNITT_RECORDER_HOME")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2] / "skills" / "cli-recorder"

PROFILES_DIR = _recorder_home() / "profiles"

_CURSOR_RE = re.compile(r'\x1b\[7m(.)\x1b\[27m')


class RecorderError(RuntimeError):
    """User-facing recorder error (clean message, no traceback)."""


# ── Recipe + profile loading ─────────────────────────────────────────────────

@dataclass
class Step:
    id: str
    label: str
    action: str
    # action-specific fields:
    text: str | None = None
    dismiss_key: str | None = None
    pause_before: float | None = None
    key: str | None = None
    pattern: str | None = None
    timeout: float | None = None
    duration: float | None = None
    # populated at runtime:
    start_s: float = 0.0
    end_s:   float = 0.0


@dataclass
class Recipe:
    title: str
    command: str
    profile: str = "generic"
    cols: int = 100
    rows: int = 28
    typing_wpm: float = 125.0
    idle_speedup: float = 4.0
    idle_threshold: float = 0.4
    idle_time_limit: float = 2.5
    # CLI-family knobs (from profile, may be empty):
    wait_for_banner: str = ""
    banner_timeout: float = 5.0
    idle_stable_secs: float = 2.0
    graceful_exit: bool = True
    modal_commands: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    # filename roots:
    name: str = ""
    recipe_path: Path = field(default_factory=Path)


def _merge(target: dict, source: dict) -> None:
    """Shallow-merge: source values override target, but only where target lacks a key."""
    for k, v in source.items():
        if k not in target:
            target[k] = v


def load_recipe(recipe_path: Path) -> Recipe:
    raw = tomllib.loads(recipe_path.read_text())
    if "recording" not in raw or "step" not in raw:
        raise RecorderError(f"{recipe_path} missing required [recording] or [[step]] blocks")

    rec_block: dict[str, Any] = dict(raw["recording"])
    profile_name = rec_block.get("profile", "generic")
    profile_path = PROFILES_DIR / f"{profile_name}.toml"
    if not profile_path.exists():
        raise RecorderError(f"profile '{profile_name}' not found at {profile_path}")
    profile_raw = tomllib.loads(profile_path.read_text())

    # Merge profile [recording] under recipe [recording] — recipe wins on conflict.
    if "recording" in profile_raw:
        _merge(rec_block, profile_raw["recording"])

    # CLI-family block in the profile lives under a name like [claude_code], [shell], [tui].
    family = next((k for k in profile_raw if k != "recording"), None)
    family_block = profile_raw.get(family, {}) if family else {}

    # Step parsing
    steps: list[Step] = []
    for raw_step in raw["step"]:
        s = Step(
            id=raw_step["id"],
            label=raw_step["label"],
            action=raw_step["action"],
            text=raw_step.get("text"),
            dismiss_key=raw_step.get("dismiss_key"),
            pause_before=raw_step.get("pause_before"),
            key=raw_step.get("key"),
            pattern=raw_step.get("pattern"),
            timeout=raw_step.get("timeout"),
            duration=raw_step.get("duration"),
        )
        # Auto-fill dismiss_key for known modal commands if the recipe didn't set it.
        if (s.action == "type_prompt"
                and s.dismiss_key is None
                and family_block.get("modal_commands")
                and s.text is not None
                and s.text.split()[0] in family_block["modal_commands"]):
            s.dismiss_key = "Escape"
        steps.append(s)

    # Effective lookup: recipe [recording] > profile family block > default.
    # Lets a recipe override e.g. wait_for_banner without changing profiles.
    def _eff(key: str, default: Any) -> Any:
        if key in rec_block:
            return rec_block[key]
        return family_block.get(key, default)

    return Recipe(
        title=rec_block["title"],
        command=rec_block["command"],
        profile=profile_name,
        cols=rec_block.get("cols", 100),
        rows=rec_block.get("rows", 28),
        typing_wpm=rec_block.get("typing_wpm", 125.0),
        idle_speedup=rec_block.get("idle_speedup", 4.0),
        idle_threshold=rec_block.get("idle_threshold", 0.4),
        idle_time_limit=rec_block.get("idle_time_limit", 2.5),
        wait_for_banner=_eff("wait_for_banner", ""),
        banner_timeout=_eff("banner_timeout", 5.0),
        idle_stable_secs=_eff("idle_stable_secs", 2.0),
        graceful_exit=_eff("graceful_exit", True),
        modal_commands=_eff("modal_commands", []),
        steps=steps,
        name=recipe_path.stem.replace(".recipe", ""),
        recipe_path=recipe_path,
    )


# ── tmux helpers ─────────────────────────────────────────────────────────────

def tmux(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["tmux", *args], capture_output=True, text=True)


def pane_target(session: str) -> str:
    return session


def capture_pane(session: str) -> str:
    return tmux("capture-pane", "-t", pane_target(session), "-p").stdout


def session_exists(session: str) -> bool:
    return tmux("has-session", "-t", session).returncode == 0


def kill_session(session: str) -> None:
    tmux("kill-session", "-t", session)


def send_key(session: str, key: str) -> None:
    """Send a single named key (no -l flag → tmux looks up Enter, Escape, etc.)"""
    tmux("send-keys", "-t", pane_target(session), key, "")


def type_text(session: str, text: str, wpm: float) -> None:
    """Type text character-by-character at ~wpm, then press Enter."""
    base = 60.0 / (wpm * 5)
    for char in text:
        if char in ' \t':
            jitter = random.uniform(1.0, 2.5)
        elif char in '.,?!:;':
            jitter = random.uniform(1.2, 2.0)
        else:
            jitter = random.uniform(0.5, 1.5)
        time.sleep(base * jitter)
        tmux("send-keys", "-l", "-t", pane_target(session), char)
    time.sleep(random.uniform(0.3, 0.8))
    send_key(session, "Enter")


# ── Idle detection ───────────────────────────────────────────────────────────

def wait_for_banner(session: str, banner: str, timeout: float) -> bool:
    if not banner:
        return True
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if banner in capture_pane(session):
            return True
        time.sleep(0.5)
    print(f"  [warn] banner '{banner}' never appeared", file=sys.stderr)
    return False


def wait_for_stable(session: str, stable_secs: float, timeout: float = 30.0) -> bool:
    """Wait until pane content has not changed for stable_secs (no Phase 1)."""
    deadline = time.monotonic() + timeout
    last: str | None = None
    stable_since: float | None = None
    while time.monotonic() < deadline:
        current = capture_pane(session)
        if current != last:
            last = current
            stable_since = time.monotonic()
        elif stable_since and (time.monotonic() - stable_since) >= stable_secs:
            return True
        time.sleep(IDLE_POLL_INTERVAL)
    return True  # treat as stable on timeout


def wait_for_idle(session: str, stable_secs: float, timeout: float = IDLE_TIMEOUT_SECS) -> bool:
    """Phase 1 (≤15s): wait for any change. Phase 2: wait for stability."""
    baseline = capture_pane(session)
    phase1_deadline = time.monotonic() + 15.0
    full_deadline = time.monotonic() + timeout

    while time.monotonic() < phase1_deadline:
        if capture_pane(session) != baseline:
            break
        time.sleep(IDLE_POLL_INTERVAL)
    else:
        return True  # already idle

    last: str | None = None
    stable_since: float | None = None
    while time.monotonic() < full_deadline:
        current = capture_pane(session)
        if current != last:
            last = current
            stable_since = time.monotonic()
        elif stable_since and (time.monotonic() - stable_since) >= stable_secs:
            return True
        time.sleep(IDLE_POLL_INTERVAL)
    print("  [warn] timeout waiting for idle", file=sys.stderr)
    return False


def wait_for_pattern(session: str, pattern: str, timeout: float) -> bool:
    rx = re.compile(pattern)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if rx.search(capture_pane(session)):
            return True
        time.sleep(IDLE_POLL_INTERVAL)
    print(f"  [warn] pattern {pattern!r} never matched", file=sys.stderr)
    return False


# ── Session lifecycle ────────────────────────────────────────────────────────

def spawn_session(recipe: Recipe, session: str, cast_path: Path) -> None:
    if session_exists(session):
        kill_session(session)
    wrapper = Path("/tmp/cli-recorder-wrapper.sh")
    wrapper.write_text(
        f"#!/bin/sh\nexport TERM=xterm-256color\n"
        f"exec asciinema rec --overwrite --quiet "
        f"--idle-time-limit {recipe.idle_time_limit} "
        f"--title {shlex.quote(recipe.title)} "
        f"--command {shlex.quote(recipe.command)} "
        f"{shlex.quote(str(cast_path.resolve()))}\n"
    )
    wrapper.chmod(0o755)
    start_cmd = f"script -q -c {shlex.quote(str(wrapper))} /dev/null"
    tmux("new-session", "-d", "-s", session,
         "-x", str(recipe.cols), "-y", str(recipe.rows),
         start_cmd)
    tmux("set-option", "-t", session, "status", "off")
    print(f"  [spawn] session '{session}' (recording → {cast_path})")


def wait_for_session_end(session: str, timeout: float = 45.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not session_exists(session):
            return True
        time.sleep(0.5)
    return False


# ── Step execution ───────────────────────────────────────────────────────────

def run_steps(recipe: Recipe, session: str, dry_run: bool, t_origin: float) -> None:
    """Execute each step, recording start_s/end_s relative to t_origin."""
    if not dry_run:
        if not wait_for_banner(session, recipe.wait_for_banner, recipe.banner_timeout):
            print("  ABORT — banner never appeared", file=sys.stderr)
            return
        time.sleep(2.0)  # let prompt initialise

    n = len(recipe.steps)
    for i, step in enumerate(recipe.steps, 1):
        step.start_s = time.monotonic() - t_origin
        print(f"\n  [step {i}/{n}] {step.id}: {step.label!r} ({step.action})")

        if step.action == "type_prompt":
            if not dry_run:
                wait_for_idle(session, recipe.idle_stable_secs)
                time.sleep(step.pause_before if step.pause_before is not None else 1.5)
                type_text(session, step.text or "", recipe.typing_wpm)
                time.sleep(2.0)
                if step.dismiss_key:
                    wait_for_stable(session, recipe.idle_stable_secs)
                    time.sleep(0.5)
                    print(f"           ↩ dismissing with {step.dismiss_key!r}")
                    send_key(session, step.dismiss_key)
                    time.sleep(1.0)

        elif step.action == "send_key":
            if not dry_run:
                time.sleep(step.pause_before if step.pause_before is not None else 0.5)
                send_key(session, step.key or "")
                time.sleep(0.5)

        elif step.action == "wait_for_pattern":
            if not dry_run:
                wait_for_pattern(session, step.pattern or "", step.timeout or 60)

        elif step.action == "pause":
            if not dry_run:
                time.sleep(step.duration or 0)

        else:
            print(f"  [warn] unknown action {step.action!r}", file=sys.stderr)

        step.end_s = time.monotonic() - t_origin


def graceful_exit_session(recipe: Recipe, session: str, dry_run: bool) -> None:
    """Send Escape (clears any modal) then type 'exit' / '/exit' to close cleanly."""
    if dry_run:
        return
    print("\n  [done] waiting for final response…")
    wait_for_idle(session, recipe.idle_stable_secs)
    if not recipe.graceful_exit:
        return
    time.sleep(3.0)
    send_key(session, "Escape")
    time.sleep(0.5)
    exit_cmd = "/exit" if recipe.command.endswith("claude") else "exit"
    print(f"  [done] typing {exit_cmd!r} — waiting for asciinema to flush cast…")
    type_text(session, exit_cmd, recipe.typing_wpm)


# ── Cast post-processing ─────────────────────────────────────────────────────

def postprocess_cast(src: Path, dst: Path, recipe: Recipe) -> tuple[float, float]:
    """Strip artifacts AND compress idle gaps. Returns (saved_s, final_s)."""
    with open(src) as f:
        header = json.loads(f.readline())
        events = [json.loads(line) for line in f
                  if line.strip() and '\x00' not in line]

    out: list[list] = []
    saved = 0.0
    for e in events:
        delta, typ, data = e[0], e[1], e[2]
        if typ == 'o':
            data = _CURSOR_RE.sub(r'\1', data)
            data = data.replace('\xa0', ' ')
        if delta > recipe.idle_threshold:
            new_delta = recipe.idle_threshold + (delta - recipe.idle_threshold) / recipe.idle_speedup
            saved += delta - new_delta
            delta = new_delta
        out.append([delta, typ, data])

    with open(dst, 'w') as f:
        f.write(json.dumps(header) + '\n')
        for e in out:
            f.write(json.dumps(e) + '\n')

    final = sum(e[0] for e in out)
    print(f"  [post] cleaned cast → {dst} (idle saved: -{saved:.1f}s, final {final:.1f}s)")
    return saved, final


# ── Scene index sidecar ──────────────────────────────────────────────────────

def write_scene_index(recipe: Recipe, cast_path: Path, total_s: float, idx_path: Path,
                      saved_s: float) -> None:
    """Translate raw step timestamps to post-compression timestamps.

    Step start_s/end_s were captured pre-compression. After idle compression,
    the cast is shorter by `saved_s`. We can't know exactly where each
    step lands in the compressed timeline without replaying — but we can scale
    proportionally as a v0 (good enough for chapter markers; refine later).
    """
    raw_total = recipe.steps[-1].end_s if recipe.steps else 0.0
    scale = (total_s / raw_total) if raw_total > 0 else 1.0

    payload = {
        "recipe":     str(recipe.recipe_path),
        "cast":       cast_path.name,
        "title":      recipe.title,
        "duration_s": round(total_s, 3),
        "fps_hint":   30,
        "post_processing": {
            "idle_threshold": recipe.idle_threshold,
            "idle_speedup":   recipe.idle_speedup,
            "idle_saved_s":   round(saved_s, 3),
            "scale_applied":  round(scale, 4),
        },
        "steps": [
            {
                "id":      s.id,
                "label":   s.label,
                "action":  s.action,
                "start_s": round(s.start_s * scale, 3),
                "end_s":   round(s.end_s * scale, 3),
            }
            for s in recipe.steps
        ],
    }
    idx_path.write_text(json.dumps(payload, indent=2))
    print(f"  [post] wrote scene index → {idx_path}")


# ── Rendering (optional) ─────────────────────────────────────────────────────

def render_gif(cast_path: Path, gif_path: Path) -> None:
    if not shutil.which("agg"):
        print("  [skip] agg not on PATH — skipping GIF render")
        return
    print(f"  [agg] rendering {gif_path} …")
    subprocess.run([
        "agg",
        "--font-family", "JetBrainsMono Nerd Font Mono,JetBrains Mono,Menlo",
        "--font-size", "26", "--line-height", "1.4",
        "--cols", "100", "--rows", "28",
        "--theme", "nord",
        "--idle-time-limit", "3.0",
        "--last-frame-duration", "5",
        "--fps-cap", "30",
        str(cast_path), str(gif_path),
    ], check=False)


def render_mp4(gif_path: Path, mp4_path: Path) -> None:
    if not (shutil.which("ffmpeg") and gif_path.exists()):
        return
    print(f"  [ffmpeg] rendering {mp4_path} …")
    subprocess.run([
        "ffmpeg", "-i", str(gif_path),
        "-vf", "fps=30,scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
        "-movflags", "faststart", "-y", str(mp4_path),
    ], capture_output=True, check=False)


# ── Main ─────────────────────────────────────────────────────────────────────

def add_parser(sub) -> None:
    ap = sub.add_parser("record", description=__doc__,
                        formatter_class=argparse.RawDescriptionHelpFormatter,
                        help="Record a CLI session from a recipe into an asciicast.")
    ap.add_argument("recipe", type=Path, help="path to recipe.toml")
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="output dir (default: $CLAUDE_PROJECT_DIR/.recordings/<recipe-name>/)")
    ap.add_argument("--session", default=None,
                    help="tmux session name (default: cli-rec-<recipe-name>)")
    ap.add_argument("--dry-run", action="store_true",
                    help="parse recipe and print steps; don't record")
    ap.add_argument("--no-render", action="store_true",
                    help="skip GIF/MP4 rendering")
    ap.add_argument("--keep", action="store_true",
                    help="keep the tmux session after run (useful for debugging)")
    ap.set_defaults(func=run_record)


def _default_out_dir(name: str) -> Path:
    base = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    return base / ".recordings" / name


def run_record(args) -> int:
    if not args.recipe.exists():
        raise RecorderError(f"recipe not found: {args.recipe}")

    recipe = load_recipe(args.recipe)
    out_dir = args.out_dir or _default_out_dir(recipe.name)
    session = args.session or f"cli-rec-{recipe.name}"
    out_dir.mkdir(parents=True, exist_ok=True)
    cast_path  = out_dir / f"{recipe.name}.cast"
    clean_path = out_dir / f"{recipe.name}.clean.cast"
    index_path = out_dir / f"{recipe.name}.scene-index.json"
    gif_path   = out_dir / f"{recipe.name}.gif"
    mp4_path   = out_dir / f"{recipe.name}.mp4"

    print("\n[cli-recorder]")
    print(f"  recipe    : {args.recipe}")
    print(f"  profile   : {recipe.profile}")
    print(f"  command   : {recipe.command}")
    print(f"  steps     : {len(recipe.steps)}")
    print(f"  out-dir   : {out_dir}")
    print(f"  session   : {session}")
    print(f"  dry-run   : {args.dry_run}")
    print()

    if args.dry_run:
        print("  [dry-run] would execute these steps:")
        for i, s in enumerate(recipe.steps, 1):
            extra = ""
            if s.action == "type_prompt":
                extra = f" text={s.text!r}" + (f" dismiss={s.dismiss_key!r}" if s.dismiss_key else "")
            elif s.action == "send_key":
                extra = f" key={s.key!r}"
            elif s.action == "wait_for_pattern":
                extra = f" pattern={s.pattern!r} timeout={s.timeout}"
            elif s.action == "pause":
                extra = f" duration={s.duration}"
            print(f"    {i:>2}. [{s.action:<16}] {s.id:<20} {s.label!r}{extra}")
        return 0

    spawn_session(recipe, session, cast_path)
    t_origin = time.monotonic()
    try:
        run_steps(recipe, session, args.dry_run, t_origin)
        graceful_exit_session(recipe, session, args.dry_run)
    finally:
        if not args.keep:
            print("  [waiting] session ending (asciinema flushing)…")
            if not wait_for_session_end(session, timeout=45.0):
                time.sleep(3.0)
                kill_session(session)

    if not cast_path.exists():
        raise RecorderError(f"cast file was not produced at {cast_path}")

    saved, total = postprocess_cast(cast_path, clean_path, recipe)
    clean_path.replace(cast_path)
    write_scene_index(recipe, cast_path, total, index_path, saved)

    if not args.no_render:
        render_gif(cast_path, gif_path)
        render_mp4(gif_path, mp4_path)

    print(f"\n[done] artifacts in {out_dir}")
    return 0
