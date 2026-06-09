
# Remotion Audio & Timing

Generate voiceover and create frame-accurate timing manifests from storyboards. Audio must be generated before implementation so animations sync precisely to spoken words.

## Why Audio First

- Need exact word/phrase timestamps to sync animations
- Total duration determines video length and frame count
- Beat timings must align with audio, not the other way around

## Process

### Step 1: Extract Voiceover Scripts

Read the project's `docs/STORYBOARD.md` and extract all VO text from beats in scene order.

**Every beat must have a voiceover line.** If any beat has empty VO, stop and ask the user to provide one before proceeding — silent beats cause dead air.

**Sub-beat audio:** If a beat contains multiple animated elements with their own text (e.g., a step list where each step is read aloud), extract those as separate VO lines too. Each needs its own audio file.

### Step 2: Generate Audio (Per Beat)

Generate a **separate audio file per beat**, not one monolithic file. This ensures each beat's `<Audio>` plays inside its own `<Sequence>` without clipping.

**If the `feinklang` CLI is available (ElevenLabs-backed):**
```bash
# Source API key, then generate per beat
source ~/.env 2>/dev/null
feinklang tts --text "[Beat 1 VO text]" --out public/vo-beat1-1.mp3
feinklang tts --text "[Beat 2 VO text]" --out public/vo-beat1-2.mp3
# ... for each beat
```

**If `feinklang` is not on PATH:**
Instruct the user to provide audio files:
> "Please record voiceover audio for each beat and place them in `public/` as `vo-beat1-1.mp3`, `vo-beat1-2.mp3`, etc."

**Cannot proceed without audio files.** Audio is mandatory for timing.

### Step 3: Audio Analysis

Measure duration of **each beat's audio file** using ffprobe:

```bash
ffprobe -v quiet -show_entries format=duration -of csv=p=0 public/vo-beat1-1.mp3
ffprobe -v quiet -show_entries format=duration -of csv=p=0 public/vo-beat1-2.mp3
# ... for each beat
```

Note: `@remotion/media-utils` `getAudioDurationInSeconds()` requires Remotion's rendering context. Use `ffprobe` at this stage since we're working from the CLI before the project is fully set up.

### Step 4: Beat Timing Calculation

**Critical rule: each beat's duration must be >= its audio duration.** If a beat's audio is 2.9 seconds, the beat needs at least 90 frames at 30fps.

Process:
1. Measure each beat's audio duration with ffprobe
2. Add padding (0.3-0.5s) per beat for visual breathing room
3. Sum all beat durations to get total video duration
4. Calculate total frames: `Math.ceil(totalDuration * fps)`
5. Assign frame ranges so no beat clips its audio

**If total duration exceeds target:** Ask user which beats to trim VO text for, regenerate those clips.

**If total duration is under target:** Distribute extra time proportionally, giving more breathing room to visually complex beats.

### Step 4b: Sub-Beat Timing (Step Lists, Multi-Element Beats)

When a beat contains multiple animated elements each with their own VO (e.g., a step list), calculate `stepTimings` in the manifest:

1. Generate a separate audio file per sub-element (`vo-step1.mp3`, `vo-step2.mp3`, etc.)
2. Measure each clip's duration with ffprobe
3. Sequence them: each sub-element starts after the previous one's audio finishes (+ 0.1-0.3s gap)
4. **Never use arbitrary frame spacing** (e.g., "every 14 frames") — always derive from actual audio duration

```typescript
// In timing.ts
stepTimings: [
  { startFrame: 66, durationFrames: 42 },   // step1: starts after intro VO
  { startFrame: 108, durationFrames: 42 },   // step2: starts after step1 audio ends
  { startFrame: 150, durationFrames: 36 },   // step3: etc.
],
```

Then in the component, use `<Sequence>` per step:
```tsx
{stepAudioFiles.map((file, i) => (
  <Sequence key={file} from={stepTimings[i].startFrame} durationInFrames={stepTimings[i].durationFrames}>
    <Audio src={staticFile(file)} volume={0.85} />
  </Sequence>
))}
```

**The animation for each step must also use `stepTimings[i].startFrame`** — the card slides in at exactly the frame its audio starts playing.

### Step 5: Generate Timing Manifest

Write timing manifest to `src/timing.ts`. See [timing-manifest-template.md](timing-manifest-template.md) for the exact format.

The manifest must include an `audioFile` field per beat pointing to its individual audio file:

```typescript
beats: [
  {
    id: "beat1-1",
    title: "The Hook",
    startFrame: 0,
    endFrame: 60,
    startTime: 0,
    endTime: 2,
    voiceover: "Debugging the old way...",
    audioFile: "vo-beat1-1.mp3",  // per-beat audio
  },
  // ...
]
```

Read [audio-sync-patterns.md](audio-sync-patterns.md) for patterns on syncing animations to audio.

### Step 6: Generate Transcript

Write `docs/TRANSCRIPT.md` with all VO lines in order. This serves two purposes:
- **Manual recording:** User can read the script themselves instead of using TTS
- **Subtitles/captions:** Source text for adding captions later

Format:
```markdown
# [Video Title] — Transcript

**Duration:** ~Xs | **Voice:** [name] | **Format:** [resolution]

---

## Beat 1: [Title] (0:00 - 0:XX)

**[Stage direction — what's on screen]**
> Voiceover line here.

---

## Full Script (for manual recording)

1. "First line."
2. "Second line."
...
```

### Output

- `public/vo-beat*.mp3` — Audio files (one per beat)
- `public/vo-step*.mp3` — Sub-beat audio files (if applicable)
- `src/timing.ts` — Frame-accurate timing manifest
- `docs/TRANSCRIPT.md` — Full transcript for manual recording or captions

Commit all to git.
