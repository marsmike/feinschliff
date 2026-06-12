"""Post-render verification — evidence before 'done'.

Checks: output duration == source duration (we never cut), and either:
  - unscored: audio stream is bit-identical to the source (D6 — voice
    untouched until the M4 scoring phase replaces the mix deliberately).
  - scored:   audio stream present + the mix's integrated loudness within
    MIX_DELTA_WINDOW of the SOURCE voice loudness (D-M4-8, voice-relative).
    The voice is untouched in the mix, so the mix must track it: an absolute
    LUFS target would fail every honest mix of a quiet recording, while the
    relative window catches the real failure modes at any input level —
    amix attenuating the voice (delta below the floor) or a bed/SFX gain bug
    swamping it (delta above the ceiling).
"""
from __future__ import annotations

from pathlib import Path

from feinschnitt.edit import EditError
from feinschnitt.edit.render import _run, ffprobe_meta
from feinschnitt.edit.score import MIX_DELTA_WINDOW, measure_lufs

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


def run(source: Path, output: Path, scored: bool = False) -> None:
    if not output.exists():
        raise EditError(f"output not found: {output}")
    out_meta = ffprobe_meta(output)
    problems = check_durations(ffprobe_meta(source)["duration"],
                               out_meta["duration"])
    if scored:
        # D-M4-8: scored mode — audio stream presence + voice-relative loudness.
        if not out_meta["has_audio"]:
            problems.append("scored output has no audio stream")
        else:
            mix_lufs = measure_lufs(output)
            voice_lufs = measure_lufs(source)
            delta = mix_lufs - voice_lufs
            lo, hi = MIX_DELTA_WINDOW
            if not (lo <= delta <= hi):
                problems.append(
                    f"scored mix {mix_lufs:.1f} LUFS is {delta:+.1f} dB vs the "
                    f"source voice {voice_lufs:.1f} LUFS — outside window "
                    f"[{lo:+.0f}, {hi:+.0f}] dB (the mix must track the "
                    "untouched voice)"
                )
    else:
        if _audio_md5(source) != _audio_md5(output):
            problems.append("audio stream differs from source — the voice track "
                            "must be untouched (pre-scoring)")
    if problems:
        raise EditError("verify failed:\n  " + "\n  ".join(problems))
    print(f"verify OK — {output}")
