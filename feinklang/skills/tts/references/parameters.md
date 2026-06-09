# feinklang CLI reference

## `feinklang tts`

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--text` | yes | — | Text to speak |
| `--out` / `--output` | no | timestamped temp file | Output file path |
| `--voice-id` / `--voice` | no | `Hale` (`wWWn96OtTHu1sn8SRGEr`) | Voice ID or name: `Hale`, `Mike`, `Lea`, or any voice ID |
| `--model-id` / `--model` | no | `eleven_multilingual_v2` | Model (see below) |
| `--format` | no | `mp3_44100_128` | Output format (see below) |
| `--stability` | no | `0.5` | Voice stability 0–1 |
| `--similarity-boost` | no | `0.75` | Voice similarity 0–1 |
| `--speed` | no | `1.0` | Speech rate 0.7–1.2 |
| `--play` | no | off | Play audio locally after generation |

### Models

| Model | Use case |
|-------|----------|
| `eleven_multilingual_v2` | Default. High quality, multilingual. |
| `eleven_v3` | Latest premium model. |
| `eleven_flash_v2_5` | Fast generation for previews. |

### Output formats

`mp3_44100_128` (default), `mp3_44100_192`, `pcm_44100`, `wav_44100`,
`opus_48000_64`. Use `opus_48000_64` for WhatsApp voice messages (OGG/Opus
plays natively).

## `feinklang voices`

| Flag | Description |
|------|-------------|
| `--category` | Filter by `cloned`, `professional`, or `premade` |
| `--search` | Search voices by name |

Output lines: `[<category>] <name> → <voice_id>`.

## Examples

```bash
# Simple speech
feinklang tts --text "Welcome to the future of voice." --out hello.mp3

# Different voice, premium model, higher bitrate
feinklang tts --text "Premium audio" --voice-id Lea --model-id eleven_v3 --format mp3_44100_192

# Fast preview
feinklang tts --text "Quick test" --model-id eleven_flash_v2_5

# Generate and play immediately
feinklang tts --text "Listen to this" --play
```
