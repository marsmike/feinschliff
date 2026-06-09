#!/bin/bash
# extract-keyframes.sh — Extract representative frames from rendered scene MP4s
#
# For each scene, extracts frames at: first frame, 25%, 50%, 75%, last frame
# These frames are used by evaluation agents to assess visual quality.
#
# Usage:
#   ./extract-keyframes.sh <out-dir> <Scene0> [Scene1 ...]
#
# Output:
#   <out-dir>/eval/Scene0/frame_000.png  (first frame)
#   <out-dir>/eval/Scene0/frame_025.png  (25%)
#   <out-dir>/eval/Scene0/frame_050.png  (50%)
#   <out-dir>/eval/Scene0/frame_075.png  (75%)
#   <out-dir>/eval/Scene0/frame_100.png  (last frame)

set -euo pipefail

OUT_DIR="${1:?Usage: $0 <out-dir> <Scene0> [Scene1 ...]}"
shift
SCENES=("$@")

if [ ${#SCENES[@]} -lt 1 ]; then
  echo "Error: provide at least one scene name" >&2
  exit 1
fi

EVAL_DIR="$OUT_DIR/eval"
mkdir -p "$EVAL_DIR"

for scene in "${SCENES[@]}"; do
  MP4="$OUT_DIR/${scene}.mp4"
  if [ ! -f "$MP4" ]; then
    echo "SKIP: $MP4 not found"
    continue
  fi

  SCENE_EVAL_DIR="$EVAL_DIR/$scene"
  mkdir -p "$SCENE_EVAL_DIR"

  # Get duration and frame count
  DURATION=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 "$MP4")
  FPS=$(ffprobe -v quiet -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$MP4")
  # r_frame_rate is a fraction like 30/1
  FPS_NUM=$(echo "$FPS" | cut -d'/' -f1)
  FPS_DEN=$(echo "$FPS" | cut -d'/' -f2)
  FPS_VAL=$(echo "scale=2; $FPS_NUM / $FPS_DEN" | bc)
  TOTAL_FRAMES=$(echo "scale=0; $DURATION * $FPS_VAL / 1" | bc)

  # Extract at 0%, 25%, 50%, 75%, 100% (clamped to last frame)
  PERCENTAGES=(0 25 50 75 100)
  TIMESTAMPS=()

  for pct in "${PERCENTAGES[@]}"; do
    if [ "$pct" -eq 100 ]; then
      # Last frame: slightly before end to avoid black frame
      TS=$(echo "scale=4; $DURATION - (1 / $FPS_VAL)" | bc)
    else
      TS=$(echo "scale=4; $DURATION * $pct / 100" | bc)
    fi
    TIMESTAMPS+=("$TS")

    OUTFILE="$SCENE_EVAL_DIR/frame_$(printf '%03d' $pct).png"
    ffmpeg -y -ss "$TS" -i "$MP4" -frames:v 1 -q:v 2 "$OUTFILE" 2>/dev/null

    # Also get frame number for metadata
    FRAME_NUM=$(echo "scale=0; $TS * $FPS_VAL / 1" | bc)
    echo "  $scene @ ${pct}% (frame $FRAME_NUM, ${TS}s) → $(basename "$OUTFILE")"
  done

  # Write metadata for evaluation agents
  cat > "$SCENE_EVAL_DIR/meta.json" <<EOF
{
  "scene": "$scene",
  "source": "$MP4",
  "duration_seconds": $DURATION,
  "fps": $FPS_VAL,
  "total_frames": $TOTAL_FRAMES,
  "frames": [
    {"file": "frame_000.png", "percent": 0,   "timestamp": ${TIMESTAMPS[0]}},
    {"file": "frame_025.png", "percent": 25,  "timestamp": ${TIMESTAMPS[1]}},
    {"file": "frame_050.png", "percent": 50,  "timestamp": ${TIMESTAMPS[2]}},
    {"file": "frame_075.png", "percent": 75,  "timestamp": ${TIMESTAMPS[3]}},
    {"file": "frame_100.png", "percent": 100, "timestamp": ${TIMESTAMPS[4]}}
  ]
}
EOF
done

echo ""
echo "Keyframes extracted to: $EVAL_DIR/"
echo "Scenes: ${SCENES[*]}"
