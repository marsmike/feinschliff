# Audio & Voice-Over

## Audio in Remotion

### Basic audio

```tsx
import { Audio, staticFile } from "remotion";

<Audio src={staticFile("music.mp3")} volume={0.5} />
```

### Per-frame volume (fade in/out)

```tsx
import { Audio, staticFile, interpolate } from "remotion";

<Audio
  src={staticFile("voiceover.mp3")}
  volume={(f) =>
    interpolate(f, [0, 15], [0, 1], { extrapolateRight: "clamp" })
  }
/>
```

### Multiple audio tracks

Just add multiple `<Audio>` components — they mix automatically:

```tsx
<>
  <Audio src={staticFile("voiceover.mp3")} volume={1} />
  <Audio src={staticFile("bgmusic.mp3")} volume={0.15} />
</>
```

### Trim audio

```tsx
<Audio
  src={staticFile("long-track.mp3")}
  trimBefore={30}   // skip first 30 frames
  trimAfter={300}   // stop at frame 300
/>
```

Note: `startFrom`/`endAt` are deprecated in v4. Use `trimBefore`/`trimAfter`.

## Voice-Over SOP (feinklang tts)

### Step 1: Generate audio

Using the feinklang TTS CLI (a bare command on PATH):

```
feinklang tts --text "Your narration script goes here. Keep sentences short and clear." --out public/voiceover.mp3
```

If `feinklang` is not on PATH / `ELEVENLABS_API_KEY` is unset, use any audio file — just place it in `public/`.

### Step 2: Get audio duration

```typescript
import { getAudioDurationInSeconds } from "@remotion/media-utils";
import { staticFile } from "remotion";

// In calculateMetadata (recommended):
export const myComposition = () => (
  <Composition
    id="Explainer"
    component={Explainer}
    width={1920}
    height={1080}
    fps={30}
    durationInFrames={300} // fallback
    calculateMetadata={async () => {
      const duration = await getAudioDurationInSeconds(
        staticFile("voiceover.mp3")
      );
      return { durationInFrames: Math.ceil(duration * 30) };
    }}
  />
);
```

### Step 3: Add audio to composition

```tsx
import { Audio, staticFile } from "remotion";

export const Explainer: React.FC = () => (
  <>
    <Audio src={staticFile("voiceover.mp3")} />
    {/* ... visual content ... */}
  </>
);
```

### Step 4: Sync visuals to audio

Define section timestamps manually (listen to the audio and note when each section starts):

```typescript
const fps = 30;
const toFrame = (seconds: number) => Math.round(seconds * fps);

const sections = {
  intro: { start: toFrame(0), duration: toFrame(3.5) },
  explanation: { start: toFrame(3.5), duration: toFrame(8.5) },
  demo: { start: toFrame(12), duration: toFrame(13) },
  outro: { start: toFrame(25), duration: toFrame(5) },
};
```

Then use `<Sequence>` to time each visual section:

```tsx
<Sequence from={sections.intro.start} durationInFrames={sections.intro.duration}>
  <TitleSlide segments={[...]} />
</Sequence>

<Sequence from={sections.explanation.start} durationInFrames={sections.explanation.duration}>
  <ExplanationScene />
</Sequence>

<Sequence from={sections.demo.start} durationInFrames={sections.demo.duration}>
  <DemoScene />
</Sequence>
```

Keep it simple. Manual timestamps are fine — you can adjust by re-rendering stills at section boundaries to check alignment.

## Batch Voice Generation Script

For multi-scene videos, generate all audio files at once by looping the
`feinklang tts` CLI (a bare command on PATH) — no inline API code needed:

```bash
# scripts/generate-voiceover.sh
set -euo pipefail
mkdir -p public/audio

declare -A scenes=(
  [scene1]="AI coding assistants are incredible at writing code..."
  [scene2]="The visual feedback loop changes everything..."
  # Add more scenes
)

for name in "${!scenes[@]}"; do
  echo "Generating ${name}..."
  feinklang tts --text "${scenes[$name]}" --out "public/audio/${name}.mp3"
  echo "  → public/audio/${name}.mp3"
done
```

Run: `bash scripts/generate-voiceover.sh`

Pass `--voice-id`, `--model-id`, `--stability`, `--similarity-boost`, `--speed`, `--format`, or `--play` to `feinklang tts` (see `feinklang tts --help` / `feinklang voices`).
