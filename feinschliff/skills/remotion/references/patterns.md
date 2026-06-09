# Remotion Patterns Reference

Curated patterns from the official Remotion skills. These are the patterns you need most often for educational explainer videos.

## Transitions (between scenes)

Requires: `npm install @remotion/transitions`

```tsx
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { wipe } from "@remotion/transitions/wipe";

// Transitions REDUCE total duration: 60 + 60 - 15 = 105 frames
<TransitionSeries>
  <TransitionSeries.Sequence durationInFrames={60}>
    <SceneA />
  </TransitionSeries.Sequence>
  <TransitionSeries.Transition
    presentation={fade()}
    timing={linearTiming({ durationInFrames: 15 })}
  />
  <TransitionSeries.Sequence durationInFrames={60}>
    <SceneB />
  </TransitionSeries.Sequence>
</TransitionSeries>
```

Available presentations: `fade()`, `slide({ direction: "from-left" })`, `wipe({ direction: "from-left" })`, `flip()`, `clockWipe()`.

## Spring Presets

```tsx
import { spring, useCurrentFrame, useVideoConfig } from "remotion";

const { fps } = useVideoConfig();
const frame = useCurrentFrame();

// Smooth (cards, backgrounds) — damping: 200
const smooth = spring({ frame, fps, config: { damping: 200 } });

// Snappy (badges, small elements) — damping: 20, stiffness: 200
const snappy = spring({ frame, fps, config: { damping: 20, stiffness: 200 } });

// Bouncy (attention-grabbing) — damping: 8
const bouncy = spring({ frame, fps, config: { damping: 8 } });

// Heavy (large elements) — damping: 15, stiffness: 80, mass: 2
const heavy = spring({ frame, fps, config: { damping: 15, stiffness: 80, mass: 2 } });

// With delay and fixed duration:
const delayed = spring({ frame, fps, delay: 20, durationInFrames: 40, config: { damping: 200 } });
```

## Stagger Pattern

Animate items appearing one by one with consistent delay:

```tsx
const STAGGER_DELAY = 8; // frames between each item

{items.map((item, i) => {
  const progress = spring({
    frame,
    fps,
    delay: i * STAGGER_DELAY,
    config: { damping: 200 },
  });

  return (
    <div
      key={i}
      style={{
        opacity: progress,
        transform: `translateY(${(1 - progress) * 30}px)`,
      }}
    >
      <Card>{item}</Card>
    </div>
  );
})}
```

## Sequencing

```tsx
import { Series, Sequence } from "remotion";

// Series: sequential clips, no manual offset math
<Series>
  <Series.Sequence durationInFrames={45}>
    <Intro />
  </Series.Sequence>
  <Series.Sequence durationInFrames={60}>
    <Main />
  </Series.Sequence>
  <Series.Sequence offset={-15} durationInFrames={60}>
    <Outro />  {/* overlaps previous by 15 frames */}
  </Series.Sequence>
</Series>

// Sequence: manual positioning (better for beat-driven timing)
<Sequence from={0} durationInFrames={90} name="Intro">
  <Intro />
</Sequence>
<Sequence from={90} durationInFrames={120} name="Main">
  <Main />  {/* useCurrentFrame() resets to 0 here */}
</Sequence>
```

**Key rule:** `useCurrentFrame()` resets to 0 inside each `<Sequence>`. This is by design.

Use `premountFor={fps}` on `<Series.Sequence>` to preload the next scene 1 second early.

## Audio Visualization

Requires: `npm install @remotion/media-utils`

```tsx
import { useWindowedAudioData, visualizeAudio } from "@remotion/media-utils";
import { useCurrentFrame, useVideoConfig, staticFile } from "remotion";

const frame = useCurrentFrame();
const { fps } = useVideoConfig();

// Get windowed audio data (efficient for long files)
const { audioData, dataOffsetInSeconds } = useWindowedAudioData({
  src: staticFile("audio.wav"),
  frame,
  fps,
  windowInSeconds: 30,
});

// Extract frequency bars (0-1 range, low indices = bass)
const frequencies = visualizeAudio({
  fps,
  frame,
  audioData,
  numberOfSamples: 256, // must be power of 2
  optimizeFor: "speed",
  dataOffsetInSeconds,
});

// Bass-reactive scale (use frequencies[0]-[3] for bass)
const bassLevel = frequencies.slice(0, 4).reduce((a, b) => a + b, 0) / 4;
const scale = 1 + bassLevel * 0.3;
```

### Waveform visualization

```tsx
import { visualizeAudioWaveform } from "@remotion/media-utils";
import { createSmoothSvgPath } from "@remotion/paths";

const waveform = visualizeAudioWaveform({
  fps, frame, audioData,
  numberOfSamples: 128,
  dataOffsetInSeconds,
});

const points = waveform.map((v, i) => [
  (i / waveform.length) * width,
  height / 2 + v * height * 0.4,
]);

const path = createSmoothSvgPath({ points });
// Use in <svg><path d={path} /></svg>
```

## Dynamic Metadata (audio-driven duration)

```tsx
import { Composition, getAudioDurationInSeconds, staticFile } from "remotion";

<Composition
  id="Explainer"
  component={Explainer}
  width={1920}
  height={1080}
  fps={30}
  durationInFrames={300} // fallback
  calculateMetadata={async () => {
    const duration = await getAudioDurationInSeconds(staticFile("voiceover.mp3"));
    return { durationInFrames: Math.ceil(duration * 30) };
  }}
/>
```

## Text Layout

```tsx
import { measureText } from "@remotion/layout-utils";

const { width, height } = measureText({
  text: "Hello World",
  fontFamily: "Inter",
  fontSize: 48,
  fontWeight: "600",
  letterSpacing: "0px",
});
// Use to pre-calculate dimensions, prevent overflow
```

## Parametrized Compositions (Zod)

```tsx
import { z } from "zod";
import { zColor } from "@remotion/zod-types";

const MySchema = z.object({
  title: z.string(),
  accentColor: zColor(),
  items: z.array(z.object({ label: z.string(), value: z.number() })),
});

<Composition
  id="MyComp"
  component={MyComp}
  schema={MySchema}
  defaultProps={{ title: "Hello", accentColor: "#a3e635", items: [] }}
  // ...
/>
```

## Key Rules

1. **Never use CSS animations** — always `interpolate()` or `spring()` for frame-perfect rendering
2. **Always clamp** — use `extrapolateRight: "clamp"` to prevent values overshooting
3. **Use `<Img>` not `<img>`** — Remotion's component waits for load before frame capture
4. **`staticFile()` for public/ assets** — ensures correct paths in all environments
5. **`delayRender()` / `continueRender()`** — required for any async operation (fonts, data, images from URLs)
6. **Scale with fps** — `fps * 2` for 2 seconds, not `60` (which assumes 30fps)
