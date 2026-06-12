"""Render orchestration — proxy, fingerprint cache, lock, Remotion, remux.

Ladder (pick the cheapest tier for the iteration loop):
  preview — 720p-class proxy + scaled comp; fast; the default.
  final   — source resolution.

Invariants:
  D5 — the render fingerprint is written ONLY after a fully successful
       render+remux, so a crash never fakes a cache hit.
  D6 — after every render the ORIGINAL audio stream is stream-copied back
       in, so the voice track stays bit-identical to the source.
  D10 — one render at a time, machine-global PID-aware lock.
  Source contract (engine Task 8): OffthreadVideo only loads bundle-served
  assets, so the render source is hardlinked into edit-engine/public/ and
  props carry the bare filename (resolved via staticFile()).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from feinschnitt.edit import EditError
from feinschnitt.edit import align as alignmod
from feinschnitt.edit import captions as captionsmod
from feinschnitt.edit import plan as planmod
from feinschnitt.edit import props as propsmod
from feinschnitt.edit import theme as thememod
from feinschnitt.edit import transcribe as transcribemod
from feinschnitt.edit import zoom as zoommod
from feinschnitt.edit.lint import IMAGE_KINDS, lint_beats, lint_captions_config, lint_score_config
from feinschnitt.edit.workdir import (mark_stage_done, stage_is_fresh,
                                      stage_key, workdir_for)

LOCK = Path.home() / ".cache" / "feinschnitt" / "edit" / ".render.lock"
PROXY_PARAMS = "scale=-2:min(1280,ih)|libx264|veryfast|crf20|an"


def should_score(quality: str, flag: bool, config: dict | None) -> bool:
    """Return True when the score pipeline should run for this render.

    Rules (D-M4-1):
      - Preview ALWAYS returns False — the iteration loop must stay fast and
        voice-pure regardless of flag or config.
      - Final returns True when flag is True AND config doesn't disable scoring
        (config None, or config without "enabled", or config with enabled=True).
    """
    if quality != "final":
        return False
    if not flag:
        return False
    if config is not None and config.get("enabled") is False:
        return False
    return True


def engine_dir() -> Path:
    env = os.environ.get("FEINSCHNITT_EDIT_ENGINE")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3] / "edit-engine"


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)
    except FileNotFoundError as exc:
        raise EditError(f"required tool not found: {cmd[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise EditError(f"{cmd[0]} failed: {exc.stderr[-2000:]}") from exc


def ffprobe_meta(video: Path) -> dict:
    out = _run(["ffprobe", "-v", "error", "-show_entries",
                "stream=codec_type,width,height", "-show_entries",
                "format=duration", "-of", "json", str(video)]).stdout
    try:
        data = json.loads(out)
        streams = data.get("streams", [])
        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        if not video_streams:
            raise EditError(f"no video stream in {video}")
        v = video_streams[0]
        return {"duration": round(float(data["format"]["duration"]), 3),
                "width": int(v["width"]), "height": int(v["height"]),
                "has_audio": any(s.get("codec_type") == "audio"
                                 for s in streams)}
    except EditError:
        raise
    except (KeyError, IndexError, TypeError, ValueError,
            json.JSONDecodeError) as exc:
        raise EditError(f"ffprobe output unreadable for {video}: {exc}") from exc


def ensure_proxy(video: Path, wd: Path) -> Path:
    """720p-class decode proxy — eliminates the 4K-decode-per-frame cost."""
    proxy = wd / "source_720p.mp4"
    marker = wd / ".proxy"
    key = stage_key(video.resolve(), video.stat().st_mtime_ns, PROXY_PARAMS)
    if stage_is_fresh(marker, key) and proxy.exists():
        return proxy
    _run(["ffmpeg", "-y", "-i", str(video),
          "-vf", "scale=-2:'min(1280,ih)'", "-c:v", "libx264", "-preset",
          "veryfast", "-crf", "20", "-an", str(proxy)])
    mark_stage_done(marker, key)
    return proxy


def render_fingerprint(
    props_bytes: bytes,
    quality: str,
    source_mtime: int,
    asset_stats: list[tuple[str, int]] | None = None,
) -> str:
    h = hashlib.sha1()
    h.update(props_bytes)
    h.update(quality.encode())
    h.update(str(source_mtime).encode())
    src = engine_dir() / "src"
    files = sorted(src.rglob("*")) if src.exists() else []
    for f in files:
        if f.is_file():
            h.update(str(f.relative_to(src)).encode())
            h.update(str(f.stat().st_mtime_ns).encode())
    lock_file = engine_dir() / "package-lock.json"
    if lock_file.exists():
        h.update(str(lock_file.stat().st_mtime_ns).encode())
    if asset_stats:
        for path, mtime_ns in asset_stats:
            h.update(path.encode())
            h.update(str(mtime_ns).encode())
    return h.hexdigest()


def _stage_file(src: Path, engine: Path, name: str) -> str:
    """Hardlink (or copy) src into engine/public/<name>; unlinks first."""
    public = engine / "public"
    public.mkdir(exist_ok=True)
    dest = public / name
    if dest.exists():
        dest.unlink()
    try:
        os.link(src, dest)
    except OSError:
        shutil.copy2(src, dest)
    return name


def _stage_source(video_or_proxy: Path, engine: Path, name: str) -> str:
    """Hardlink (or copy) the render source into the engine's public/ dir."""
    return _stage_file(video_or_proxy, engine, name)


def _stage_assets(
    beats: list[dict],
    plan_dir: Path,
    engine: Path,
    prefix: str,
) -> tuple[list[dict], list[tuple[str, int]]]:
    """Stage every image beat's file into edit-engine/public/ and return
    (beats-copy with image_path rewritten to the bare staged name,
     [(resolved_source_path, mtime_ns), ...] for fingerprinting).

    The aligned plan on disk keeps authored paths (debuggability); only the
    props copy gets staged names.  Staged names are collision-safe per
    video+beat: <prefix>-asset-<index><suffix>.
    """
    staged: list[dict] = []
    asset_stats: list[tuple[str, int]] = []
    for i, beat in enumerate(beats):
        b = dict(beat)
        if b.get("kind") in IMAGE_KINDS:
            raw = Path(str(b.get("image_path") or ""))
            resolved = raw if raw.is_absolute() else plan_dir / raw
            if not resolved.is_file():
                raise EditError(
                    f"beat {i}: image not found during staging: {resolved}")
            name = f"{prefix}-asset-{i}{resolved.suffix.lower()}"
            _stage_file(resolved, engine, name)
            b["image_path"] = name
            asset_stats.append((str(resolved.resolve()),
                                 resolved.stat().st_mtime_ns))
        staged.append(b)
    return staged, asset_stats


def _acquire_lock() -> None:
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    if LOCK.exists():
        pid = LOCK.read_text().strip()
        if pid.isdigit() and Path(f"/proc/{pid}").exists():
            raise EditError(f"another render is running (pid {pid}) — renders are "
                            "strictly sequential; wait for it or remove "
                            f"{LOCK} if it is stale")
        LOCK.unlink()  # stale lock from a dead process — self-heal
    LOCK.write_text(str(os.getpid()))


def _release_lock() -> None:
    if LOCK.exists() and LOCK.read_text().strip() == str(os.getpid()):
        LOCK.unlink()


def _remux_source_audio(rendered: Path, source: Path, out: Path) -> None:
    _run(["ffmpeg", "-y", "-i", str(rendered), "-i", str(source),
          "-map", "0:v", "-map", "1:a", "-c", "copy", str(out)])


def render(video: Path, plan_path: Path, quality: str = "preview",
           brand_dir: Path | None = None, force: bool = False,
           score: bool = True) -> Path:  # noqa: A002  (shadows built-in fine here)
    if quality not in {"preview", "final"}:
        raise EditError(f"quality must be preview|final, got: {quality}")
    if not video.exists():
        raise EditError(f"video not found: {video}")
    engine = engine_dir()
    if not (engine / "package.json").exists():
        raise EditError(f"edit engine not found at {engine} — set "
                        "FEINSCHNITT_EDIT_ENGINE or run from a checkout")
    if not (engine / "node_modules").exists():
        _run(["npm", "install"], cwd=engine)

    wd = workdir_for(video)
    meta = ffprobe_meta(video)
    if not meta["has_audio"]:
        raise EditError(f"no audio stream in {video} — the edit pipeline is "
                        "voice-driven; record with sound")

    # 1. authored plan + lint gate (before expensive transcription)
    authored = planmod.load_plan(plan_path)
    errors, warnings = lint_beats(authored["beats"], meta["duration"],
                                   base_dir=plan_path.parent)
    for w in warnings:
        print(f"lint warning: {w}", file=sys.stderr)
    if errors:
        raise EditError("plan lint failed:\n  " + "\n  ".join(errors))

    # 1b. transcript (cached) — only paid after plan passes lint
    words_path = transcribemod.run(video)

    # 2. derived aligned plan (authored file is never mutated — D2)
    aligned = alignmod.run(authored, words_path, wd / "edit_plan.aligned.json")
    for b in aligned["beats"]:
        if b.get("_align") == "anchor-not-found":
            print(f"align warning: anchor not found: {b.get('speech_anchor')!r} "
                  "— beat keeps its authored timing", file=sys.stderr)

    # 2b. re-lint the ALIGNED beats — alignment shifts timing and may break
    # doctrine floors (e.g. a takeover snapping under the 1.5s floor).
    a_errors, a_warnings = lint_beats(aligned["beats"], meta["duration"],
                                      base_dir=plan_path.parent)
    for w in a_warnings:
        print(f"lint (aligned) warning: {w}", file=sys.stderr)
    if a_errors:
        raise EditError("aligned plan failed lint — alignment moved beats "
                        "outside doctrine; adjust anchors or timing:\n  "
                        + "\n  ".join(a_errors))

    # 3. zoom + captions + theme + props
    words = json.loads(words_path.read_text())["words"]
    zoom_path = wd / "zoom_plan.json"
    if not zoom_path.exists():  # hand-editable once generated
        zoom_path.write_text(json.dumps(zoommod.build_zoom_plan(words), indent=2))
    zoom = json.loads(zoom_path.read_text())

    # 3b. captions — validate config, build chunks from aligned beats + words
    # Use SOURCE meta dims for orientation (preview scaling doesn't change portrait/landscape).
    cap_errors = lint_captions_config(authored.get("captions")) \
        if "captions" in authored else []
    if cap_errors:
        raise EditError("captions config invalid:\n  " + "\n  ".join(cap_errors))

    # 3c. score config validation (alongside captions block, before render)
    score_config = authored.get("score")
    sc_errors = lint_score_config(score_config) if score_config is not None else []
    if sc_errors:
        raise EditError("score config invalid:\n  " + "\n  ".join(sc_errors))

    caps, cap_warnings = captionsmod.build_captions(
        words, aligned["beats"], authored.get("captions"),
        meta["width"], meta["height"])
    for cw in cap_warnings:
        print(f"captions warning: {cw}", file=sys.stderr)

    src_for_render = ensure_proxy(video, wd) if quality == "preview" else video
    render_meta = dict(meta)
    if quality == "preview":
        scale = min(1.0, 1280 / max(meta["width"], meta["height"]))
        render_meta["width"] = int(meta["width"] * scale) // 2 * 2
        render_meta["height"] = int(meta["height"] * scale) // 2 * 2
    staged_name = _stage_source(src_for_render, engine, f"{wd.name}-{quality}.mp4")

    beats_for_props, asset_stats = _stage_assets(
        aligned["beats"], plan_path.parent, engine, wd.name)
    aligned_for_props = dict(aligned)
    aligned_for_props["beats"] = beats_for_props

    props = propsmod.build_props(staged_name, aligned_for_props, zoom,
                                 thememod.resolve_theme(brand_dir), render_meta,
                                 captions=caps)
    props_path = wd / f"props.{quality}.json"
    props_bytes = json.dumps(props, indent=2).encode()
    props_path.write_bytes(props_bytes)

    # Deferred imports — score and sfx import _run from render at module level,
    # which creates a circular import if we import them at module level too.
    # Deferring to call-time breaks the cycle safely.
    from feinschnitt.edit import score as scoremod  # noqa: PLC0415
    from feinschnitt.edit import sfx as sfxmod      # noqa: PLC0415

    # 4. fingerprint cache — extend with score signature (D-M4-7) when scoring
    # will run.  Resolve track + cues here once so we can hash them AND pass
    # them into score() to avoid double resolution.
    suffix = "preview" if quality == "preview" else "enhanced"
    out = video.with_name(f"{video.stem}.{suffix}.mp4")
    fp_marker = wd / f".render.fp.{quality}"

    scoring_active = should_score(quality, score, score_config)
    resolved_track: "Path | None" = None
    resolved_cues: "list[dict] | None" = None
    if scoring_active:
        resolved_track, _tw = scoremod.pick_track(score_config)
        resolved_cues, _cw = sfxmod.plan_cues(aligned["beats"], caps)
        # Append score-signature entries to asset_stats for the fingerprint.
        asset_stats = list(asset_stats)
        asset_stats.append((
            "score:" + json.dumps(score_config or {}, sort_keys=True),
            0,
        ))
        if resolved_track is not None:
            asset_stats.append((
                f"score:{resolved_track}",
                resolved_track.stat().st_mtime_ns,
            ))
        for cue in resolved_cues:
            cue_path = Path(cue["path"])
            asset_stats.append((
                f"score:{cue_path}",
                cue_path.stat().st_mtime_ns,
            ))

    fp = render_fingerprint(props_bytes, quality, video.stat().st_mtime_ns,
                             asset_stats=asset_stats)
    if not force and stage_is_fresh(fp_marker, fp) and out.exists():
        print(f"render cache hit — {out}", file=sys.stderr)
        return out

    # 5. render (locked) + voice remux + optional score; fingerprint written only on success
    _acquire_lock()
    raw = wd / f"render.{quality}.raw.mp4"
    scored_sidecar = wd / f".scored.{quality}"
    try:
        _run(["npx", "remotion", "render", "src/index.ts", "EditedVideo",
              str(raw), f"--props={props_path}"], cwd=engine)
        _remux_source_audio(raw, video, out)
        if scoring_active:
            score_tmp = wd / "score.tmp.mp4"
            scored, score_warnings = scoremod.score(
                out, score_tmp,
                aligned["beats"], caps, score_config, meta["duration"],
                track=resolved_track,
                cues=resolved_cues,
            )
            for sw in score_warnings:
                print(f"score warning: {sw}", file=sys.stderr)
            if scored:
                os.replace(score_tmp, out)
                scored_sidecar.write_text("1")
            else:
                score_tmp.unlink(missing_ok=True)
                scored_sidecar.unlink(missing_ok=True)
        else:
            # Preview or --no-score: clean up any stale sidecar.
            scored_sidecar.unlink(missing_ok=True)
        mark_stage_done(fp_marker, fp)
    finally:
        raw.unlink(missing_ok=True)
        _release_lock()
    return out
