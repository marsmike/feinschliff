#!/bin/bash
# ElevenLabs Text-to-Speech
# Usage: ./tts.sh '{"text": "Hello world", ...}'

set -e

[[ -f "$HOME/.env" ]] && source "$HOME/.env"

if [ -z "${ELEVENLABS_API_KEY:-}" ]; then
  echo "Error: ELEVENLABS_API_KEY environment variable is not set." >&2
  echo "Get your API key from: https://elevenlabs.io/app/settings/api-keys" >&2
  exit 1
fi

API_BASE="https://api.elevenlabs.io"
DEFAULT_VOICE_ID="wWWn96OtTHu1sn8SRGEr"  # Hale
# Named voices for convenience
# Hale: wWWn96OtTHu1sn8SRGEr
# Mike: mxqV8Q77peldUYcdIgb0
# Lea:  M39iqBUcu1jyiwM5PfSy

JSON_INPUT="$1"

if [ -z "$JSON_INPUT" ]; then
  echo "Usage: ./tts.sh '<json>'"
  echo ""
  echo "Required:"
  echo "  text: string - Text to convert to speech"
  echo ""
  echo "Optional:"
  echo "  voice_id: string (default: Mike)"
  echo "  model_id: eleven_multilingual_v2 (default), eleven_v3, eleven_flash_v2_5"
  echo "  output: string - Output file path (default: /tmp/tts_<timestamp>.mp3)"
  echo "  format: mp3_44100_128 (default), mp3_44100_192, wav_44100, pcm_44100"
  echo "  stability: 0-1 (default: 0.5)"
  echo "  similarity_boost: 0-1 (default: 0.75)"
  echo "  speed: 0.7-1.2 (default: 1.0)"
  echo "  play: true/false (default: true)"
  exit 1
fi

# Validate JSON
if ! echo "$JSON_INPUT" | jq empty 2>/dev/null; then
  echo "Error: Invalid JSON input" >&2
  exit 1
fi

# Extract parameters
TEXT=$(echo "$JSON_INPUT" | jq -r '.text // empty')
if [ -z "$TEXT" ]; then
  echo "Error: 'text' field is required" >&2
  exit 1
fi

# Resolve named voices
RAW_VOICE=$(echo "$JSON_INPUT" | jq -r ".voice_id // \"$DEFAULT_VOICE_ID\"")
case "$RAW_VOICE" in
  mike|Mike) VOICE_ID="mxqV8Q77peldUYcdIgb0" ;;
  lea|Lea)   VOICE_ID="M39iqBUcu1jyiwM5PfSy" ;;
  *)         VOICE_ID="$RAW_VOICE" ;;
esac
MODEL_ID=$(echo "$JSON_INPUT" | jq -r '.model_id // "eleven_multilingual_v2"')
OUTPUT_FORMAT=$(echo "$JSON_INPUT" | jq -r '.format // "mp3_44100_128"')
STABILITY=$(echo "$JSON_INPUT" | jq -r '.stability // 0.5')
SIMILARITY=$(echo "$JSON_INPUT" | jq -r '.similarity_boost // 0.75')
SPEED=$(echo "$JSON_INPUT" | jq -r '.speed // 1.0')
PLAY=$(echo "$JSON_INPUT" | jq -r '.play // false')

# Determine file extension from format
case "$OUTPUT_FORMAT" in
  mp3_*) EXT="mp3" ;;
  wav_*) EXT="wav" ;;
  pcm_*) EXT="pcm" ;;
  opus_*) EXT="ogg" ;;
  *) EXT="mp3" ;;
esac

OUTPUT_FILE=$(echo "$JSON_INPUT" | jq -r '.output // empty')
if [ -z "$OUTPUT_FILE" ]; then
  TIMESTAMP=$(date +%Y%m%d_%H%M%S)
  OUTPUT_FILE="/tmp/tts_${TIMESTAMP}.${EXT}"
fi

# Build request body
REQUEST_BODY=$(jq -n \
  --arg text "$TEXT" \
  --arg model "$MODEL_ID" \
  --argjson stability "$STABILITY" \
  --argjson similarity "$SIMILARITY" \
  --argjson speed "$SPEED" \
  '{
    text: $text,
    model_id: $model,
    voice_settings: {
      stability: $stability,
      similarity_boost: $similarity,
      speed: $speed
    }
  }')

# Call ElevenLabs TTS API
HTTP_CODE=$(curl -s -w "%{http_code}" \
  -X POST "$API_BASE/v1/text-to-speech/$VOICE_ID?output_format=$OUTPUT_FORMAT" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$REQUEST_BODY" \
  --output "$OUTPUT_FILE")

if [ "$HTTP_CODE" -ne 200 ]; then
  ERROR=$(cat "$OUTPUT_FILE" 2>/dev/null)
  rm -f "$OUTPUT_FILE"
  echo "Error: API returned HTTP $HTTP_CODE" >&2
  echo "$ERROR" >&2
  exit 1
fi

FILE_SIZE=$(wc -c < "$OUTPUT_FILE" | tr -d ' ')
echo "Generated: $OUTPUT_FILE ($FILE_SIZE bytes)"
echo "Voice: $VOICE_ID | Model: $MODEL_ID | Format: $OUTPUT_FORMAT"

# Play audio on macOS
if [ "$PLAY" = "true" ] && command -v afplay &>/dev/null && { [ "$EXT" = "mp3" ] || [ "$EXT" = "wav" ]; }; then
  echo "Playing audio..."
  afplay "$OUTPUT_FILE"
fi
