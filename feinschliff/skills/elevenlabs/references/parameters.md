# TTS Parameters Reference

## JSON Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `text` | yes | — | The text to speak |
| `voice_id` | no | `wWWn96OtTHu1sn8SRGEr` (Hale) | Voice ID or name: `Hale`, `Mike`, `Lea`, or any voice ID |
| `model_id` | no | `eleven_multilingual_v2` | Model (see below) |
| `output` | no | auto-generated in `/tmp` | Output file path |
| `format` | no | `mp3_44100_128` | Output format (see below) |
| `stability` | no | `0.5` | Voice stability 0-1 |
| `similarity_boost` | no | `0.75` | Voice similarity 0-1 |
| `speed` | no | `1.2` | Speech rate 0.7-1.2 |
| `play` | no | `false` | Play audio locally after generation |

## Models

| Model | Use case |
|-------|----------|
| `eleven_multilingual_v2` | Default. High quality, multilingual. |
| `eleven_v3` | Latest premium model. |
| `eleven_flash_v2_5` | Fast generation for previews. |

## Output Formats

`mp3_44100_128` (default), `mp3_44100_192`, `pcm_44100`, `wav_44100`, `opus_48000_64`

Use `opus_48000_64` for WhatsApp voice messages — produces OGG/Opus that WhatsApp plays natively.

## Examples

```bash
# Simple speech
${CLAUDE_PLUGIN_ROOT}/skills/elevenlabs/scripts/tts.sh '{"text": "Welcome to the future of voice."}'

# Use a different voice and save to specific path
${CLAUDE_PLUGIN_ROOT}/skills/elevenlabs/scripts/tts.sh '{"text": "Hello world", "voice_id": "CwhRBWXzGAHq8TQ4Fs17", "output": "/tmp/hello.mp3"}'

# High quality with v3 model
${CLAUDE_PLUGIN_ROOT}/skills/elevenlabs/scripts/tts.sh '{"text": "Premium audio", "model_id": "eleven_v3", "format": "mp3_44100_192", "play": false}'

# Fast generation for previews
${CLAUDE_PLUGIN_ROOT}/skills/elevenlabs/scripts/tts.sh '{"text": "Quick test", "model_id": "eleven_flash_v2_5"}'
```
