#!/bin/bash
# parallel-render.sh — Parallel Remotion scene rendering with ffmpeg xfade concat
#
# Renders each Composition in parallel, then joins them with crossfade transitions.
# Supports preview mode (low-res, fast) and production mode (full-res).
#
# Usage:
#   ./parallel-render.sh [OPTIONS] <project-dir> <Scene1> <Scene2> [Scene3 ...]
#
# Options:
#   --preview         Render at 360p (360x640) with fast preset for quick preview
#   --scale <factor>  Custom scale factor (0.0-1.0), default: 1.0 (or 0.33 in preview)
#   --transition <s>  Transition duration in seconds (default: 0.5)
#   --type <name>     xfade transition type (default: fade). See ffmpeg xfade docs.
#   --crf <value>     CRF quality (default: 18, preview: 28)
#   --out <path>      Output filename (default: out/final.mp4 or out/preview.mp4)
#   --no-concat       Render scenes only, skip ffmpeg concat step
#   --warmup          Run a 1-frame still render first to cache fonts/bundles
#   --jobs <n>        Max parallel jobs (default: number of scenes)
#   --help            Show this help
#
# Examples:
#   ./parallel-render.sh ~/my-video Scene1 Scene2 Scene3
#   ./parallel-render.sh --preview ~/my-video Scene1 Scene2 Scene3 Scene4 Scene5 Scene6
#   ./parallel-render.sh --scale 0.5 --transition 0.3 --type slideleft ~/my-video Scene1 Scene2

set -euo pipefail

# ── Defaults ──────────────────────────────────────────────────────────
PREVIEW=false
SCALE=""
TRANS_DUR="0.5"
TRANS_TYPE="fade"
CRF=""
OUTPUT=""
NO_CONCAT=false
WARMUP=false
MAX_JOBS=0  # 0 = unlimited (one per scene)

# ── Parse args ────────────────────────────────────────────────────────
SCENES=()
PROJECT_DIR=""

usage() {
  sed -n '2,/^$/p' "$0" | sed 's/^# \?//'
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --preview)    PREVIEW=true; shift ;;
    --scale)      SCALE="$2"; shift 2 ;;
    --transition) TRANS_DUR="$2"; shift 2 ;;
    --type)       TRANS_TYPE="$2"; shift 2 ;;
    --crf)        CRF="$2"; shift 2 ;;
    --out)        OUTPUT="$2"; shift 2 ;;
    --no-concat)  NO_CONCAT=true; shift ;;
    --warmup)     WARMUP=true; shift ;;
    --jobs)       MAX_JOBS="$2"; shift 2 ;;
    --help|-h)    usage ;;
    -*)           echo "Unknown option: $1" >&2; exit 1 ;;
    *)
      if [ -z "$PROJECT_DIR" ]; then
        PROJECT_DIR="$1"
      else
        SCENES+=("$1")
      fi
      shift
      ;;
  esac
done

# ── Validate ──────────────────────────────────────────────────────────
if [ -z "$PROJECT_DIR" ] || [ ${#SCENES[@]} -lt 1 ]; then
  echo "Usage: $0 [OPTIONS] <project-dir> <Scene1> <Scene2> [...]" >&2
  echo "Run with --help for full usage." >&2
  exit 1
fi

PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
if [ ! -f "$PROJECT_DIR/src/index.ts" ]; then
  echo "Error: $PROJECT_DIR/src/index.ts not found. Is this a Remotion project?" >&2
  exit 1
fi

# ── Resolve settings ──────────────────────────────────────────────────
if [ "$PREVIEW" = true ]; then
  SCALE="${SCALE:-0.33}"
  CRF="${CRF:-28}"
  PRESET="ultrafast"
  OUTPUT="${OUTPUT:-$PROJECT_DIR/out/preview.mp4}"
  echo "=== PREVIEW MODE (${SCALE}x scale, crf=$CRF, $PRESET) ==="
else
  SCALE="${SCALE:-1.0}"
  CRF="${CRF:-18}"
  PRESET="slow"
  OUTPUT="${OUTPUT:-$PROJECT_DIR/out/final.mp4}"
  echo "=== PRODUCTION MODE (${SCALE}x scale, crf=$CRF, $PRESET) ==="
fi

OUT_DIR="$PROJECT_DIR/out"
LOG_DIR="$OUT_DIR/logs"
mkdir -p "$OUT_DIR" "$LOG_DIR"

SCENE_COUNT=${#SCENES[@]}
echo "Project:     $PROJECT_DIR"
echo "Scenes:      ${SCENES[*]} ($SCENE_COUNT total)"
echo "Transition:  ${TRANS_DUR}s ($TRANS_TYPE)"
echo "Output:      $OUTPUT"
echo ""

# ── Phase 0: Warmup (optional) ───────────────────────────────────────
if [ "$WARMUP" = true ]; then
  echo "=== Phase 0: Font/bundle warmup ==="
  cd "$PROJECT_DIR"
  npx remotion still src/index.ts "${SCENES[0]}" /tmp/remotion-warmup.png \
    --frame=0 --scale=0.25 --quiet 2>/dev/null || true
  echo "Warmup done."
  echo ""
fi

# ── Phase 1: Parallel render ─────────────────────────────────────────
echo "=== Phase 1: Parallel rendering ($SCENE_COUNT scenes) ==="

# Build remotion render args
build_render_cmd() {
  local scene="$1"
  local outfile="$OUT_DIR/${scene}.mp4"
  local logfile="$LOG_DIR/${scene}.log"

  echo "cd '$PROJECT_DIR' && npx remotion render src/index.ts '$scene' '$outfile' \
    --codec h264 --crf $CRF --scale $SCALE \
    2>&1 | tee '$logfile'"
}

# Launch all render jobs
PIDS=()
START_TIME=$(date +%s)

for scene in "${SCENES[@]}"; do
  CMD=$(build_render_cmd "$scene")
  echo "  Starting: $scene"
  eval "$CMD" &
  PIDS+=($!)

  # Throttle if max jobs set
  if [ "$MAX_JOBS" -gt 0 ] && [ ${#PIDS[@]} -ge "$MAX_JOBS" ]; then
    # Wait for any one job to finish before launching next
    wait -n "${PIDS[@]}" 2>/dev/null || true
  fi
done

# Wait for all jobs and collect exit codes
FAILED=()
for i in "${!PIDS[@]}"; do
  if ! wait "${PIDS[$i]}"; then
    FAILED+=("${SCENES[$i]}")
  fi
done

END_TIME=$(date +%s)
RENDER_SECS=$((END_TIME - START_TIME))

echo ""
echo "Render complete in ${RENDER_SECS}s"

# Report results
for scene in "${SCENES[@]}"; do
  OUTFILE="$OUT_DIR/${scene}.mp4"
  if [ -f "$OUTFILE" ]; then
    SIZE=$(du -sh "$OUTFILE" | cut -f1)
    DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUTFILE" 2>/dev/null || echo "?")
    echo "  $scene: ${SIZE}, ${DUR}s"
  else
    echo "  $scene: MISSING"
  fi
done

if [ ${#FAILED[@]} -gt 0 ]; then
  echo ""
  echo "FAILED scenes: ${FAILED[*]}"
  echo "Check logs in $LOG_DIR/"
  exit 1
fi

# ── Phase 2: ffmpeg xfade concat ─────────────────────────────────────
if [ "$NO_CONCAT" = true ]; then
  echo ""
  echo "Skipping concat (--no-concat). Scene files in $OUT_DIR/"
  exit 0
fi

if [ "$SCENE_COUNT" -eq 1 ]; then
  echo ""
  echo "Single scene — copying to output."
  cp "$OUT_DIR/${SCENES[0]}.mp4" "$OUTPUT"
  echo "Output: $OUTPUT"
  exit 0
fi

echo ""
echo "=== Phase 2: ffmpeg xfade concat ==="

# Get durations
declare -a DURS
for i in "${!SCENES[@]}"; do
  DURS[$i]=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUT_DIR/${SCENES[$i]}.mp4")
  echo "  ${SCENES[$i]}: ${DURS[$i]}s"
done

# Build filter graph
# For 2 scenes: simple single xfade
# For N scenes: chained xfade filters
INPUTS=""
for scene in "${SCENES[@]}"; do
  INPUTS="$INPUTS -i $OUT_DIR/${scene}.mp4"
done

if [ "$SCENE_COUNT" -eq 2 ]; then
  OFFSET=$(echo "scale=6; ${DURS[0]} - $TRANS_DUR" | bc)
  VFILTER="[0:v][1:v]xfade=transition=${TRANS_TYPE}:duration=${TRANS_DUR}:offset=${OFFSET}[vout]"

  # Check if audio streams exist
  HAS_AUDIO=true
  for scene in "${SCENES[@]}"; do
    if ! ffprobe -v quiet -select_streams a -show_entries stream=codec_type "$OUT_DIR/${scene}.mp4" 2>/dev/null | grep -q audio; then
      HAS_AUDIO=false
      break
    fi
  done

  if [ "$HAS_AUDIO" = true ]; then
    AFILTER="[0:a][1:a]acrossfade=d=${TRANS_DUR}[aout]"
    ffmpeg -y $INPUTS \
      -filter_complex "${VFILTER};${AFILTER}" \
      -map "[vout]" -map "[aout]" \
      -c:v libx264 -crf "$CRF" -preset "$PRESET" \
      -c:a aac -b:a 192k \
      "$OUTPUT"
  else
    ffmpeg -y $INPUTS \
      -filter_complex "${VFILTER}" \
      -map "[vout]" \
      -c:v libx264 -crf "$CRF" -preset "$PRESET" \
      "$OUTPUT"
  fi
else
  # N-scene chained xfade
  # OFF(n) = cumulative_duration_up_to_n - n * TRANS_DUR
  VFILTER=""
  AFILTER=""
  CUMULATIVE="${DURS[0]}"

  # Check audio availability
  HAS_AUDIO=true
  for scene in "${SCENES[@]}"; do
    if ! ffprobe -v quiet -select_streams a -show_entries stream=codec_type "$OUT_DIR/${scene}.mp4" 2>/dev/null | grep -q audio; then
      HAS_AUDIO=false
      break
    fi
  done

  # First transition: [0:v][1:v] -> [v1]
  OFFSET=$(echo "scale=6; $CUMULATIVE - $TRANS_DUR" | bc)
  VFILTER="[0:v][1:v]xfade=transition=${TRANS_TYPE}:duration=${TRANS_DUR}:offset=${OFFSET}[v1]"
  [ "$HAS_AUDIO" = true ] && AFILTER="[0:a][1:a]acrossfade=d=${TRANS_DUR}[a1]"

  LAST_VTAG="v1"
  LAST_ATAG="a1"

  # Chain remaining transitions
  for ((n=2; n<SCENE_COUNT; n++)); do
    CUMULATIVE=$(echo "scale=6; $CUMULATIVE + ${DURS[$((n-1))]}" | bc)
    OFFSET=$(echo "scale=6; $CUMULATIVE - $n * $TRANS_DUR" | bc)

    NEW_VTAG="v${n}"
    NEW_ATAG="a${n}"

    VFILTER="${VFILTER};[${LAST_VTAG}][${n}:v]xfade=transition=${TRANS_TYPE}:duration=${TRANS_DUR}:offset=${OFFSET}[${NEW_VTAG}]"
    [ "$HAS_AUDIO" = true ] && AFILTER="${AFILTER};[${LAST_ATAG}][${n}:a]acrossfade=d=${TRANS_DUR}[${NEW_ATAG}]"

    LAST_VTAG="$NEW_VTAG"
    LAST_ATAG="$NEW_ATAG"
  done

  echo "Offsets computed. Running ffmpeg..."

  if [ "$HAS_AUDIO" = true ]; then
    ffmpeg -y $INPUTS \
      -filter_complex "${VFILTER};${AFILTER}" \
      -map "[${LAST_VTAG}]" -map "[${LAST_ATAG}]" \
      -c:v libx264 -crf "$CRF" -preset "$PRESET" \
      -c:a aac -b:a 192k \
      "$OUTPUT"
  else
    ffmpeg -y $INPUTS \
      -filter_complex "${VFILTER}" \
      -map "[${LAST_VTAG}]" \
      -c:v libx264 -crf "$CRF" -preset "$PRESET" \
      "$OUTPUT"
  fi
fi

echo ""
echo "=== Done ==="
FINAL_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$OUTPUT" 2>/dev/null || echo "?")
FINAL_SIZE=$(du -sh "$OUTPUT" | cut -f1)
echo "Output: $OUTPUT ($FINAL_SIZE, ${FINAL_DUR}s)"
echo "Render time: ${RENDER_SECS}s (parallel), total wall time: $(($(date +%s) - START_TIME))s"
