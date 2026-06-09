#!/bin/bash
# AI Image Generation — Multi-provider
# Usage: ./imagine.sh '{"prompt": "...", "provider": "replicate|gemini", ...}'

set -e

# Export all vars from .env (set -a ensures they're available to subprocesses)
if [[ -f "$HOME/.env" ]]; then
  set -a
  source "$HOME/.env"
  set +a
fi

JSON_INPUT="$1"

if [ -z "$JSON_INPUT" ]; then
  echo "Usage: ./imagine.sh '<json>'"
  echo ""
  echo "Required:"
  echo "  prompt: string — Image description"
  echo ""
  echo "Optional:"
  echo "  provider: replicate (default), gemini"
  echo "  model: string — Provider-specific model"
  echo "  aspect_ratio: 1:1 (default), 16:9, 9:16, 4:3, 3:4, 3:2, 2:3"
  echo "  output: string — Output file path"
  exit 1
fi

if ! echo "$JSON_INPUT" | jq empty 2>/dev/null; then
  echo "Error: Invalid JSON input" >&2
  exit 1
fi

PROMPT=$(echo "$JSON_INPUT" | jq -r '.prompt // empty')
if [ -z "$PROMPT" ]; then
  echo "Error: 'prompt' field is required" >&2
  exit 1
fi

PROVIDER=$(echo "$JSON_INPUT" | jq -r '.provider // "replicate"')
MODEL=$(echo "$JSON_INPUT" | jq -r '.model // empty')
ASPECT_RATIO=$(echo "$JSON_INPUT" | jq -r '.aspect_ratio // "1:1"')
OUTPUT=$(echo "$JSON_INPUT" | jq -r '.output // empty')

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ---------------------------------------------------------------------------
# Replicate (Flux models)
# ---------------------------------------------------------------------------
generate_replicate() {
  if [ -z "${REPLICATE_API_KEY:-}" ]; then
    echo "Error: REPLICATE_API_KEY not set in ~/.env" >&2
    exit 1
  fi

  local model="${MODEL:-black-forest-labs/flux-schnell}"

  # kontext and some pro models only support jpg/png
  local output_format="webp"
  case "$model" in
    *kontext*|*fill*|*redux*) output_format="png" ;;
  esac

  local ext="${output_format}"
  local output_file="${OUTPUT:-/tmp/imagine_${TIMESTAMP}.${ext}}"

  echo "Provider: Replicate | Model: $model" >&2
  echo "Prompt: $PROMPT" >&2
  echo "Generating..." >&2

  local response
  response=$(curl -s -X POST \
    -H "Prefer: wait" \
    -H "Authorization: Bearer $REPLICATE_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
      --arg prompt "$PROMPT" \
      --arg aspect_ratio "$ASPECT_RATIO" \
      --arg output_format "$output_format" \
      '{input: {prompt: $prompt, aspect_ratio: $aspect_ratio, output_format: $output_format, go_fast: true}}')" \
    "https://api.replicate.com/v1/models/${model}/predictions")

  local status
  status=$(echo "$response" | jq -r '.status // "unknown"')

  if [ "$status" != "succeeded" ]; then
    local error
    error=$(echo "$response" | jq -r '.error // .detail // "Unknown error"')
    echo "Error: Replicate returned status '$status': $error" >&2
    echo "$response" | jq . >&2
    exit 1
  fi

  local image_url
  # Some models return output as array, others as string
  local output_type
  output_type=$(echo "$response" | jq -r '.output | type')
  if [ "$output_type" = "array" ]; then
    image_url=$(echo "$response" | jq -r '.output[0] // empty')
  else
    image_url=$(echo "$response" | jq -r '.output // empty')
  fi
  if [ -z "$image_url" ]; then
    echo "Error: No image URL in response" >&2
    echo "$response" | jq . >&2
    exit 1
  fi

  curl -s -o "$output_file" "$image_url"

  local predict_time
  predict_time=$(echo "$response" | jq -r '.metrics.predict_time // "?"')
  local file_size
  file_size=$(wc -c < "$output_file" | tr -d ' ')

  echo "Generated: $output_file ($file_size bytes, ${predict_time}s)"
  echo "Provider: replicate | Model: $model"
}

# ---------------------------------------------------------------------------
# Gemini (Nano Banana)
# ---------------------------------------------------------------------------
generate_gemini() {
  if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "Error: GEMINI_API_KEY not set in ~/.env" >&2
    exit 1
  fi

  local model="${MODEL:-gemini-2.5-flash-image}"
  local output_file="${OUTPUT:-/tmp/imagine_${TIMESTAMP}.png}"

  echo "Provider: Gemini | Model: $model" >&2
  echo "Prompt: $PROMPT" >&2
  echo "Generating..." >&2

  local response
  response=$(curl -s -X POST \
    -H "x-goog-api-key: $GEMINI_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
      --arg prompt "$PROMPT" \
      --arg aspect "$ASPECT_RATIO" \
      '{
        contents: [{parts: [{text: $prompt}]}],
        generationConfig: {
          responseModalities: ["IMAGE"],
          imageConfig: {aspectRatio: $aspect}
        }
      }')" \
    "https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent")

  # Check for errors
  local error
  error=$(echo "$response" | jq -r '.error.message // empty')
  if [ -n "$error" ]; then
    echo "Error: Gemini API: $error" >&2
    exit 1
  fi

  # Extract base64 image data
  local b64_data
  b64_data=$(echo "$response" | jq -r '.candidates[0].content.parts[] | select(.inlineData) | .inlineData.data // empty')
  if [ -z "$b64_data" ]; then
    echo "Error: No image data in Gemini response" >&2
    echo "$response" | jq '.candidates[0].content.parts[0]' >&2
    exit 1
  fi

  echo "$b64_data" | base64 -d > "$output_file"

  local file_size
  file_size=$(wc -c < "$output_file" | tr -d ' ')

  echo "Generated: $output_file ($file_size bytes)"
  echo "Provider: gemini | Model: $model"
}

# ---------------------------------------------------------------------------
# Route to provider
# ---------------------------------------------------------------------------
case "$PROVIDER" in
  replicate) generate_replicate ;;
  gemini)    generate_gemini ;;
  *)
    echo "Error: Unknown provider '$PROVIDER'. Use: replicate, gemini" >&2
    exit 1
    ;;
esac
