"""Post-render verification — evidence before 'done'.

Checks: output duration == source duration (we never cut), and the audio
stream is bit-identical to the source (D6 — voice untouched until the M4
scoring phase replaces the mix deliberately).
"""
from __future__ import annotations

from pathlib import Path

from feinschnitt.edit import EditError
from feinschnitt.edit.render import _run, ffprobe_meta

DURATION_TOLERANCE = 0.2


def check_durations(source_dur: float, output_dur: float) -> list[str]:
    if abs(source_dur - output_dur) > DURATION_TOLERANCE:
        return [f"duration mismatch: source {source_dur}s vs output {output_dur}s "
                f"(tolerance {DURATION_TOLERANCE}s)"]
    return []


def _audio_md5(video: Path) -> str:
    proc = _run(["ffmpeg", "-v", "error", "-i", str(video), "-map", "0:a",
                 "-c", "copy", "-f", "md5", "-"])
    return proc.stdout.strip()


def run(source: Path, output: Path) -> None:
    if not output.exists():
        raise EditError(f"output not found: {output}")
    problems = check_durations(ffprobe_meta(source)["duration"],
                               ffprobe_meta(output)["duration"])
    if _audio_md5(source) != _audio_md5(output):
        problems.append("audio stream differs from source — the voice track "
                        "must be untouched (pre-scoring)")
    if problems:
        raise EditError("verify failed:\n  " + "\n  ".join(problems))
    print(f"verify OK — {output}")
