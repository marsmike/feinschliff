#!/bin/bash
# ElevenLabs Voices - List available voices
# Usage: ./voices.sh [category|search <name>]

set -e

[[ -f "$HOME/.env" ]] && source "$HOME/.env"

if [ -z "${ELEVENLABS_API_KEY:-}" ]; then
  echo "Error: ELEVENLABS_API_KEY environment variable is not set." >&2
  echo "Get your API key from: https://elevenlabs.io/app/settings/api-keys" >&2
  exit 1
fi

API_BASE="https://api.elevenlabs.io"
ACTION="${1:-}"
SEARCH="${2:-}"

QUERY_ARGS=(--data-urlencode "page_size=50")
if [ "$ACTION" = "search" ] && [ -n "$SEARCH" ]; then
  QUERY_ARGS+=(--data-urlencode "search=$SEARCH")
elif [ -n "$ACTION" ] && [ "$ACTION" != "search" ]; then
  QUERY_ARGS+=(--data-urlencode "category=$ACTION")
fi

RESPONSE=$(curl -s -G "$API_BASE/v2/voices" "${QUERY_ARGS[@]}" -H "xi-api-key: $ELEVENLABS_API_KEY")

echo "$RESPONSE" | jq -r '.voices[] | "[\(.category)] \(.name) → \(.voice_id)"' 2>/dev/null || {
  echo "Error fetching voices:" >&2
  echo "$RESPONSE" >&2
  exit 1
}
