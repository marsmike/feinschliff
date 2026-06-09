#!/bin/bash
# evaluate-scenes.sh — Extract keyframes and prepare evaluation for sub-agents
#
# Extracts keyframes from rendered scenes, then outputs the sub-agent prompts
# that should be dispatched in parallel via the Agent tool.
#
# Usage:
#   ./evaluate-scenes.sh <project-dir> <Scene0> [Scene1 ...]
#
# Output:
#   - Extracted keyframes in <project-dir>/out/eval/<SceneN>/
#   - Evaluation prompts in <project-dir>/out/eval/<SceneN>/eval-prompt.md
#   - Summary of what to dispatch

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${1:?Usage: $0 <project-dir> <Scene0> [Scene1 ...]}"
shift
SCENES=("$@")

if [ ${#SCENES[@]} -lt 1 ]; then
  echo "Error: provide at least one scene name" >&2
  exit 1
fi

OUT_DIR="$PROJECT_DIR/out"
EVAL_DIR="$OUT_DIR/eval"
RUBRIC="$SCRIPT_DIR/eval-rubric.md"

if [ ! -f "$RUBRIC" ]; then
  echo "Error: evaluation rubric not found at $RUBRIC" >&2
  exit 1
fi

# Phase 1: Extract keyframes
echo "=== Extracting keyframes ==="
"$SCRIPT_DIR/extract-keyframes.sh" "$OUT_DIR" "${SCENES[@]}"

# Phase 2: Generate per-scene evaluation prompts
echo ""
echo "=== Generating evaluation prompts ==="

for scene in "${SCENES[@]}"; do
  SCENE_DIR="$EVAL_DIR/$scene"
  if [ ! -d "$SCENE_DIR" ]; then
    echo "SKIP: No keyframes for $scene"
    continue
  fi

  PROMPT_FILE="$SCENE_DIR/eval-prompt.md"

  # Build the prompt with frame paths
  cat > "$PROMPT_FILE" <<PROMPT
# Evaluate: $scene

You are evaluating a single scene from a YouTube Shorts video.

## Your Task

1. Read the evaluation rubric below
2. Look at each of the 5 keyframes (they are PNG images)
3. Return a structured evaluation following the rubric's output format

## Keyframes to Inspect

Read these image files in order:
PROMPT

  # Add frame paths
  for frame in "$SCENE_DIR"/frame_*.png; do
    [ -f "$frame" ] && echo "- \`$frame\`" >> "$PROMPT_FILE"
  done

  cat >> "$PROMPT_FILE" <<PROMPT

## Scene Metadata
PROMPT

  # Add metadata if available
  if [ -f "$SCENE_DIR/meta.json" ]; then
    echo '```json' >> "$PROMPT_FILE"
    cat "$SCENE_DIR/meta.json" >> "$PROMPT_FILE"
    echo '```' >> "$PROMPT_FILE"
  fi

  cat >> "$PROMPT_FILE" <<PROMPT

## Evaluation Rubric

$(cat "$RUBRIC")
PROMPT

  echo "  $scene → $PROMPT_FILE"
done

# Phase 3: Summary for orchestrator
echo ""
echo "==========================================="
echo "  READY FOR PARALLEL EVALUATION"
echo "==========================================="
echo ""
echo "Dispatch ${#SCENES[@]} sub-agents in parallel, one per scene."
echo "Each agent should:"
echo "  1. Read its eval-prompt.md"
echo "  2. Read all 5 frame_*.png images"
echo "  3. Return structured evaluation"
echo ""
echo "Scene evaluation prompts:"
for scene in "${SCENES[@]}"; do
  PROMPT_FILE="$EVAL_DIR/$scene/eval-prompt.md"
  if [ -f "$PROMPT_FILE" ]; then
    echo "  $scene: $PROMPT_FILE"
  fi
done
echo ""
echo "Results should be written to:"
for scene in "${SCENES[@]}"; do
  echo "  $EVAL_DIR/$scene/eval-result.md"
done
