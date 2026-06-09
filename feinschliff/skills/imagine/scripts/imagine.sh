#!/bin/bash
# AI Image Generation — Multi-provider
# Usage: ./imagine.sh '{"prompt": "...", "provider": "replicate|gemini|kling", ...}'

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
  echo "  provider: replicate (default), gemini, kling"
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
# Kling AI
# ---------------------------------------------------------------------------
generate_kling() {
  if [ -z "${KLING_ACCESS_KEY:-}" ] || [ -z "${KLING_SECRET_KEY:-}" ]; then
    echo "Error: KLING_ACCESS_KEY and KLING_SECRET_KEY must be set in ~/.env" >&2
    exit 1
  fi

  local model="${MODEL:-kling-v2-1}"
  local output_file="${OUTPUT:-/tmp/imagine_${TIMESTAMP}.png}"

  echo "Provider: Kling | Model: $model" >&2
  echo "Prompt: $PROMPT" >&2
  echo "Generating..." >&2

  # Generate JWT token (HS256)
  local header
  header=$(echo -n '{"alg":"HS256","typ":"JWT"}' | base64 | tr -d '=' | tr '/+' '_-' | tr -d '\n')

  local now
  now=$(date +%s)
  local exp=$((now + 1800))
  local nbf=$((now - 5))

  local payload
  payload=$(echo -n "{\"iss\":\"${KLING_ACCESS_KEY}\",\"exp\":${exp},\"nbf\":${nbf}}" | base64 | tr -d '=' | tr '/+' '_-' | tr -d '\n')

  local signature
  signature=$(echo -n "${header}.${payload}" | openssl dgst -sha256 -hmac "$KLING_SECRET_KEY" -binary | base64 | tr -d '=' | tr '/+' '_-' | tr -d '\n')

  local jwt="${header}.${payload}.${signature}"

  # Create image generation task
  local response
  response=$(curl -s -X POST \
    -H "Authorization: Bearer $jwt" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
      --arg prompt "$PROMPT" \
      --arg model "$model" \
      --arg aspect "$ASPECT_RATIO" \
      '{model_name: $model, prompt: $prompt, aspect_ratio: $aspect, n: 1}')" \
    "https://api.klingai.com/v1/images/generations")

  local task_id
  task_id=$(echo "$response" | jq -r '.data.task_id // empty')
  if [ -z "$task_id" ]; then
    local error
    error=$(echo "$response" | jq -r '.message // .error // "Unknown error"')
    echo "Error: Kling API: $error" >&2
    echo "$response" | jq . >&2
    exit 1
  fi

  echo "Task: $task_id — polling for result..." >&2

  # Poll for completion (max 60 attempts, 2s interval = 2 min timeout)
  local attempts=0
  local max_attempts=60
  local status=""
  local result=""

  while [ $attempts -lt $max_attempts ]; do
    sleep 2
    result=$(curl -s \
      -H "Authorization: Bearer $jwt" \
      "https://api.klingai.com/v1/images/generations/$task_id")

    status=$(echo "$result" | jq -r '.data.task_status // "unknown"')

    case "$status" in
      succeed)
        break
        ;;
      failed)
        local error
        error=$(echo "$result" | jq -r '.data.task_status_msg // "Generation failed"')
        echo "Error: Kling generation failed: $error" >&2
        exit 1
        ;;
      *)
        attempts=$((attempts + 1))
        ;;
    esac
  done

  if [ "$status" != "succeed" ]; then
    echo "Error: Kling generation timed out after $((max_attempts * 2))s (status: $status)" >&2
    exit 1
  fi

  # Download the image
  local image_url
  image_url=$(echo "$result" | jq -r '.data.task_result.images[0].url // empty')
  if [ -z "$image_url" ]; then
    echo "Error: No image URL in Kling response" >&2
    echo "$result" | jq . >&2
    exit 1
  fi

  curl -s -o "$output_file" "$image_url"

  local file_size
  file_size=$(wc -c < "$output_file" | tr -d ' ')

  echo "Generated: $output_file ($file_size bytes)"
  echo "Provider: kling | Model: $model"
}

# ---------------------------------------------------------------------------
# Route to provider
# ---------------------------------------------------------------------------
case "$PROVIDER" in
  replicate) generate_replicate ;;
  gemini)    generate_gemini ;;
  kling)     generate_kling ;;
  *)
    echo "Error: Unknown provider '$PROVIDER'. Use: replicate, gemini, kling" >&2
    exit 1
    ;;
esac
