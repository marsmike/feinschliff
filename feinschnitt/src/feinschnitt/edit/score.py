"""Audio score — ducked music bed, swell arc, SFX cue mix.

Levels doctrine (D-M4-4):
  voice     — untouched reference (mixed from source, bit-identical via remux).
  music bed — gained to BED_TARGET_LUFS (−26 integrated) measured per track,
              then sidechain-compressed under the voice.
  SFX cues  — each cue at SFX_GAIN_DB (−18 dBFS) via per-cue volume filter.
  swell arc — bed volume trapezoid rising to SWELL_PEAK (×1.6 ≈ +4 dB) at
              the plan's climax beat, held 2s, fallen 3s back to ×1.
  final mix — amix normalize=0 (mandatory; default would attenuate the voice).

"The plan is the cue sheet" — cues come from sfx.plan_cues, never hand-authored.
This module only runs for --quality final; preview stays voice-pure and fast.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from feinschnitt.edit import EditError
from feinschnitt.edit import sfx
from feinschnitt.edit.lint import OVERLAY_KINDS
from feinschnitt.edit.render import _run

MUSIC_DIR_ENV = "FEINSCHNITT_MUSIC_DIR"
DEFAULT_MUSIC_DIR = Path.home() / ".local" / "share" / "feinschnitt" / "music"

BED_TARGET_LUFS: float = -26.0
SFX_GAIN_DB: float = -18.0
SWELL_PEAK: float = 1.6
MIX_LUFS_WINDOW: tuple[float, float] = (-20.0, -12.0)

_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".opus"}


def music_dir() -> Path:
    """Return the music asset directory, respecting FEINSCHNITT_MUSIC_DIR."""
    env = os.environ.get(MUSIC_DIR_ENV)
    return Path(env) if env else DEFAULT_MUSIC_DIR


def measure_lufs(path: Path) -> float:
    """Run loudnorm analysis on *path* and return the integrated loudness (LUFS).

    Raises EditError when the output cannot be parsed.
    """
    result = _run([
        "ffmpeg", "-hide_banner", "-nostats",
        "-i", str(path),
        "-af", "loudnorm=print_format=json",
        "-f", "null", "-",
    ])
    stderr = result.stderr
    # loudnorm prints a JSON block to stderr — extract the last {...} block
    # that contains "input_i" (the integrated loudness key).
    match = None
    for m in re.finditer(r"\{[^{}]*\}", stderr, re.DOTALL):
        if "input_i" in m.group():
            match = m
    if match is None:
        raise EditError(f"loudness analysis failed for {path}")
    try:
        data = json.loads(match.group())
        return float(data["input_i"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise EditError(f"loudness analysis failed for {path}") from exc


def find_climax(beats: list[dict]) -> float | None:
    """Return the climax timestamp (seconds) for the swell arc.

    Priority (D-M4-5):
      1. The earliest quote_pull beat (by start_sec).
      2. The LAST takeover beat (kind not in OVERLAY_KINDS), by start_sec.
      3. None — no swell.

    Bool start_sec values are rejected (bool is a subclass of int).
    """
    def _start(b: dict) -> float | None:
        v = b.get("start_sec")
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return None
        return float(v)

    quote_pulls = [
        b for b in beats
        if b.get("kind") == "quote_pull" and _start(b) is not None
    ]
    if quote_pulls:
        return _start(min(quote_pulls, key=lambda b: _start(b)))  # type: ignore[arg-type]

    takeovers = [
        b for b in beats
        if b.get("kind") not in OVERLAY_KINDS and _start(b) is not None
    ]
    if takeovers:
        return _start(max(takeovers, key=lambda b: _start(b)))  # type: ignore[arg-type]

    return None


def _swell_value(t: float, climax: float, duration: float) -> float:
    """Pure-Python trapezoid — used to generate and test the swell expression.

    Breakpoints (all clamped to [0, duration]):
      r0      = max(0, climax − 6)   — rise start (volume = 1.0)
      climax  = climax               — rise end / hold start (volume = SWELL_PEAK)
      h1      = min(duration, climax + 2) — hold end / fall start
      f1      = min(duration, h1 + 3)    — fall end (volume = 1.0)

    Zero-width segments (e.g. r0 == climax) are collapsed: volume jumps
    straight to SWELL_PEAK at climax with no ramp.
    """
    r0 = max(0.0, climax - 6.0)
    h1 = min(duration, climax + 2.0)
    f1 = min(duration, h1 + 3.0)
    s = SWELL_PEAK

    if t <= r0:
        return 1.0
    if t < climax:
        span = climax - r0
        if span <= 0.0:
            return s
        return 1.0 + (s - 1.0) * (t - r0) / span
    if t <= h1:
        return s
    if t < f1:
        span = f1 - h1
        if span <= 0.0:
            return s
        return s - (s - 1.0) * (t - h1) / span
    return 1.0


def swell_expr(climax: float, duration: float) -> str:
    """Build an ffmpeg `volume=eval=frame:volume='...'` expression for the swell arc.

    The expression is a nested if(lt(t,...)) trapezoid matching _swell_value.
    Zero-width segments are collapsed (degenerate cases where r0==climax, etc.).
    """
    r0 = max(0.0, climax - 6.0)
    h1 = min(duration, climax + 2.0)
    f1 = min(duration, h1 + 3.0)
    s = SWELL_PEAK

    # Format floats to 6 significant digits — clean but unambiguous.
    def _f(v: float) -> str:
        return f"{v:.6g}"

    # Rise segment: linear from 1.0 at r0 to s at climax.
    rise_span = climax - r0
    if rise_span > 0.0:
        rise_expr = f"1+{_f(s - 1.0)}*(t-{_f(r0)})/{_f(rise_span)}"
    else:
        rise_expr = _f(s)

    # Fall segment: linear from s at h1 to 1.0 at f1.
    fall_span = f1 - h1
    if fall_span > 0.0:
        fall_expr = f"{_f(s)}-{_f(s - 1.0)}*(t-{_f(h1)})/{_f(fall_span)}"
    else:
        fall_expr = _f(s)

    # Innermost: after f1 → 1.0; before f1 → fall; before h1 → SWELL_PEAK;
    # before climax → rise; before r0 → 1.0.
    # Build inside-out.
    expr = (
        f"if(lt(t,{_f(r0)}),1,"
        f"if(lt(t,{_f(climax)}),{rise_expr},"
        f"if(lt(t,{_f(h1)}),{_f(s)},"
        f"if(lt(t,{_f(f1)}),{fall_expr},"
        f"1))))"
    )
    return expr


def pick_track(config: dict | None) -> tuple[Path | None, list[str]]:
    """Return (track_path | None, warnings).

    Config with a "music" key → that file in music_dir().
    No config name → alphabetically first audio file in music_dir()
    (signature-track convention: name it 00-*).
    Empty or missing dir → (None, [warning]).
    """
    warnings: list[str] = []
    d = music_dir()

    if config and config.get("music"):
        name = config["music"]
        path = d / name
        if not path.is_file():
            warnings.append(
                f"score: music track {name!r} not found in {d} — bed skipped"
            )
            return None, warnings
        return path, warnings

    # Signature-track convention: alphabetically first audio file.
    if not d.is_dir():
        warnings.append(
            f"score: music dir {d} not found — bed skipped"
        )
        return None, warnings

    candidates = sorted(
        f for f in d.iterdir()
        if f.is_file() and f.suffix.lower() in _AUDIO_EXTENSIONS
    )
    if not candidates:
        warnings.append(
            f"score: music dir {d} is empty — bed skipped"
        )
        return None, warnings

    return candidates[0], warnings


def build_filtergraph(
    bed: bool,
    n_cues: int,
    bed_gain_db: float,
    swell: str | None,
    cue_delays_ms: list[int],
    duration: float,
) -> str:
    """Build the ffmpeg -filter_complex string (pure — no I/O).

    Input index layout:
      0  — video_with_voice (audio = the pristine voice mix)
      1  — music bed track (only when bed=True; looped with -stream_loop -1)
      1+ — SFX cues (index = 1 + i when no bed; 2 + i when bed)

    Returns the filter_complex string.
    normalize=0 is mandatory — default amix attenuates the voice.
    """
    parts: list[str] = []

    if bed:
        # Split voice into two pads: [voice] for amix, [sc] for sidechain.
        parts.append("[0:a]asplit=2[voice][sc];")

        # Bed chain: gain → trim to duration → swell envelope.
        bed_chain = f"[1:a]volume={bed_gain_db:.2f}dB,atrim=0:{duration:.6g}"
        if swell is not None:
            bed_chain += f",volume=eval=frame:volume='{swell}'"
        bed_chain += "[bedlvl];"
        parts.append(bed_chain)

        # Sidechain compress: bed ducked under voice.
        parts.append(
            "[bedlvl][sc]sidechaincompress="
            "threshold=0.02:ratio=6:attack=20:release=400[duck];"
        )

        cue_base_idx = 2
        mix_inputs_list = ["[voice]", "[duck]"]
    else:
        cue_base_idx = 1
        mix_inputs_list = ["[0:a]"]

    # SFX cue chains.
    for i, ms in enumerate(cue_delays_ms):
        idx = cue_base_idx + i
        parts.append(
            f"[{idx}:a]volume={SFX_GAIN_DB:.0f}dB,"
            f"adelay={ms}|{ms}[fx{i}];"
        )
        mix_inputs_list.append(f"[fx{i}]")

    # amix: all streams; duration=first pins length to the voice; normalize=0 mandatory.
    n_inputs = len(mix_inputs_list)
    mix_inputs = "".join(mix_inputs_list)
    parts.append(
        f"{mix_inputs}amix=inputs={n_inputs}:duration=first:normalize=0[mix]"
    )

    return "".join(parts)


def score(
    video_with_voice: Path,
    out: Path,
    beats: list[dict],
    captions: list[dict],
    config: dict | None,
    duration: float,
) -> tuple[bool, list[str]]:
    """Mix music bed + SFX cues into video_with_voice and write to out.

    Returns (True, warnings) when scoring ran; (False, warnings) when skipped
    (caller keeps the voice-only output unchanged).

    Steps:
      1. Resolve track + cues; skip if neither available.
      2. Measure bed LUFS; compute gain to BED_TARGET_LUFS.
      3. Find climax → swell expression.
      4. Build filtergraph + single ffmpeg command.
      5. Write out.
    """
    warnings: list[str] = []

    track, pick_warnings = pick_track(config)
    warnings.extend(pick_warnings)

    cues, cue_warnings = sfx.plan_cues(beats, captions)
    warnings.extend(cue_warnings)

    if track is None and not cues:
        return False, warnings

    # Compute bed gain.
    bed_gain_db = 0.0
    if track is not None:
        lufs = measure_lufs(track)
        bed_gain_db = BED_TARGET_LUFS - lufs

    # Swell arc.
    climax = find_climax(beats)
    swell = swell_expr(climax, duration) if climax is not None else None

    # Cue delays (convert float seconds → integer milliseconds).
    cue_delays_ms = [int(round(c["at"] * 1000)) for c in cues]

    filtergraph = build_filtergraph(
        bed=track is not None,
        n_cues=len(cues),
        bed_gain_db=bed_gain_db,
        swell=swell,
        cue_delays_ms=cue_delays_ms,
        duration=duration,
    )

    # Build ffmpeg command.
    cmd: list[str] = ["ffmpeg", "-hide_banner", "-y"]
    cmd += ["-i", str(video_with_voice)]
    if track is not None:
        cmd += ["-stream_loop", "-1", "-i", str(track)]
    for cue in cues:
        cmd += ["-i", cue["path"]]
    cmd += [
        "-filter_complex", filtergraph,
        "-map", "0:v", "-c:v", "copy",
        "-map", "[mix]", "-c:a", "aac", "-b:a", "192k",
        "-y", str(out),
    ]

    _run(cmd)
    return True, warnings
