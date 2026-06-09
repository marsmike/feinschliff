# Transition Catalog

Scene transition types for Remotion videos with implementation code and narrative-purpose mapping. All examples target 30fps, 1080x1920 (9:16 vertical).

---

## 1. TransitionSeries API (Core Pattern)

`TransitionSeries` replaces `Sequence`-based hard cuts. Drop-in replacement that supports animated transitions between scenes.

```tsx
import { TransitionSeries, linearTiming, springTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";

export const MainVideo: React.FC = () => {
  return (
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
  );
};
```

**Duration math:** Transitions REDUCE total duration. Both scenes play simultaneously during the transition window.

```
Two 60-frame sequences + 15-frame transition = 60 + 60 - 15 = 105 total frames
Three 90-frame sequences + two 15-frame transitions = 90 + 90 + 90 - 15 - 15 = 240 total frames

General formula:
totalFrames = sum(allSequenceDurations) - sum(allTransitionDurations)
```

---

## 2. Built-in Presentations

| Presentation | Import | Options | Best Use |
|---|---|---|---|
| `fade()` | `@remotion/transitions/fade` | none | Universal dissolve. Topic progression, calm moments. |
| `slide()` | `@remotion/transitions/slide` | `direction`: `"from-left"` `"from-right"` `"from-top"` `"from-bottom"` | Scene progression, spatial movement, hook entries. |
| `wipe()` | `@remotion/transitions/wipe` | `direction`: `"from-left"` `"from-right"` `"from-top"` `"from-bottom"` `"from-top-left"` `"from-top-right"` `"from-bottom-left"` `"from-bottom-right"` | Reveals, before/after comparisons. |
| `flip()` | `@remotion/transitions/flip` | `direction`: `"from-left"` `"from-right"` `"from-top"` `"from-bottom"` | Card flip metaphor, A/B comparisons. |
| `clockWipe()` | `@remotion/transitions/clock-wipe` | `width`, `height` (required) | Dramatic reveals, countdowns. |
| `iris()` | `@remotion/transitions/iris` | `width`, `height` (required) | Spotlight/focus transitions, dramatic zoom-ins. |
| `none()` | `@remotion/transitions/none` | none | Pair with `useTransitionProgress()` for fully custom transitions. |

### Usage with options

```tsx
import { slide } from "@remotion/transitions/slide";
import { wipe } from "@remotion/transitions/wipe";
import { clockWipe } from "@remotion/transitions/clock-wipe";
import { iris } from "@remotion/transitions/iris";
import { none } from "@remotion/transitions/none";

// Directional slide
slide({ direction: "from-bottom" })

// Diagonal wipe
wipe({ direction: "from-top-left" })

// Clock wipe — requires canvas dimensions
clockWipe({ width: 1080, height: 1920 })

// Iris — requires canvas dimensions
iris({ width: 1080, height: 1920 })

// None — invisible transition, use with useTransitionProgress()
none()
```

---

## 3. Custom Presentations

Custom presentations implement the `TransitionPresentation` interface. Each returns entering/exiting style objects.

### zoomPunch

Entering scene scales from 0.86 to 1 with cubic ease. Exiting scene scales 1 to 1.08 and fades out. High-energy moment transition for short-form vertical.

```tsx
// src/transitions/zoomPunch.ts
import type { TransitionPresentation, TransitionPresentationComponentProps } from "@remotion/transitions";
import React from "react";
import { AbsoluteFill, interpolate } from "remotion";

const ZoomPunchPresentation: React.FC<TransitionPresentationComponentProps<Record<string, never>>> = ({
  children,
  presentationDirection,
  presentationProgress,
}) => {
  const isEntering = presentationDirection === "entering";

  const scale = isEntering
    ? interpolate(presentationProgress, [0, 1], [0.86, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: (t) => 1 - Math.pow(1 - t, 3), // cubic ease-out
      })
    : interpolate(presentationProgress, [0, 1], [1, 1.08], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });

  const opacity = isEntering
    ? interpolate(presentationProgress, [0, 0.3], [0, 1], {
        extrapolateRight: "clamp",
      })
    : interpolate(presentationProgress, [0.4, 1], [1, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });

  return (
    <AbsoluteFill
      style={{
        transform: `scale(${scale})`,
        opacity,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

export const zoomPunch = (): TransitionPresentation<Record<string, never>> => {
  return {
    component: ZoomPunchPresentation,
    props: {},
  };
};
```

### diagonalReveal

Dark panel sweeps right with a skewed leading edge and a glowing accent line. Stylish, branded feel for short-form vertical.

```tsx
// src/transitions/diagonalReveal.ts
import type { TransitionPresentation, TransitionPresentationComponentProps } from "@remotion/transitions";
import React from "react";
import { AbsoluteFill, interpolate } from "remotion";

interface DiagonalRevealProps {
  accentColor?: string;
}

const DiagonalRevealPresentation: React.FC<
  TransitionPresentationComponentProps<DiagonalRevealProps>
> = ({ children, presentationDirection, presentationProgress, passedProps }) => {
  const isEntering = presentationDirection === "entering";
  const accent = passedProps.accentColor ?? "#00FF88";

  if (isEntering) {
    // Incoming scene: revealed as the panel sweeps past
    const clipX = interpolate(presentationProgress, [0, 1], [-30, 110], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

    return (
      <AbsoluteFill
        style={{
          clipPath: `polygon(${clipX - 20}% 0%, ${clipX}% 0%, ${clipX - 20}% 100%, ${clipX - 40}% 100%)`,
        }}
      >
        {children}
      </AbsoluteFill>
    );
  }

  // Exiting scene: dark panel with skewed edge sweeps over
  const panelX = interpolate(presentationProgress, [0, 1], [-120, 110], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: (t) => 1 - Math.pow(1 - t, 2), // ease-out quad
  });

  const glowOpacity = interpolate(presentationProgress, [0.2, 0.5, 0.8], [0, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill>
      {children}
      {/* Dark sweep panel */}
      <AbsoluteFill
        style={{
          background: "#0A0A0A",
          clipPath: `polygon(${panelX}% 0%, ${panelX + 30}% 0%, ${panelX + 10}% 100%, ${panelX - 20}% 100%)`,
        }}
      />
      {/* Accent glow line on leading edge */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(135deg, transparent ${panelX + 8}%, ${accent} ${panelX + 10}%, transparent ${panelX + 12}%)`,
          opacity: glowOpacity,
          mixBlendMode: "screen",
        }}
      />
    </AbsoluteFill>
  );
};

export const diagonalReveal = (
  props: DiagonalRevealProps = {}
): TransitionPresentation<DiagonalRevealProps> => {
  return {
    component: DiagonalRevealPresentation,
    props,
  };
};
```

**Usage:**

```tsx
<TransitionSeries.Transition
  presentation={zoomPunch()}
  timing={springTiming({ config: { damping: 200 }, durationInFrames: 16 })}
/>

<TransitionSeries.Transition
  presentation={diagonalReveal({ accentColor: theme.green })}
  timing={linearTiming({ durationInFrames: 18 })}
/>
```

---

## 4. Narrative-to-Transition Mapping

| Purpose | Transition | Frames | Why |
|---|---|---|---|
| Hook entry | `slide({ direction: "from-bottom" })` | 12-15 | Matches vertical scroll gesture, feels native |
| Topic progression | `fade()` | 12-15 | Neutral, does not compete with content |
| Before/after | `wipe({ direction: "from-left" })` | 18-20 | Literal left-to-right reveal |
| Dramatic reveal | `iris({ width: 1080, height: 1920 })` | 20-25 | Spotlight draws focus to center |
| Energy burst | `zoomPunch()` | 15-18 | Scale punch grabs attention |
| Brand close | `fade()` + hold | 20-30 | Calm resolution, fade to end card |
| Segment change | `slide({ direction: "from-right" })` | 12-15 | Forward progression |
| Flashback / rewind | `slide({ direction: "from-left" })` | 12-15 | Backwards movement = going back |
| Comparison flip | `flip({ direction: "from-right" })` | 18-20 | Card metaphor, A vs B |
| Countdown beat | `clockWipe({ width: 1080, height: 1920 })` | 20-25 | Circular sweep = time |

---

## 5. Timing Rules

### Frame budgets

| Content type | Max transition frames | Notes |
|---|---|---|
| YouTube Shorts (9:16) | 20 frames (0.67s) | Pacing must stay tight |
| Explainer / tutorial | 25 frames (0.83s) | Slightly more breathing room |
| Absolute max | 30 frames (1.0s) | Never exceed this |

### Spring presets for transitions

```tsx
import { springTiming, linearTiming } from "@remotion/transitions";

// Smooth, no bounce — default for most transitions
springTiming({ config: { damping: 200 }, durationInFrames: 15 })

// Snappy — fast UI-style transitions
springTiming({ config: { damping: 200, stiffness: 300 }, durationInFrames: 12 })

// Bouncy — sparingly, for attention-grabbing moments only
springTiming({ config: { damping: 10 }, durationInFrames: 20 })

// Linear — mechanical, clock-like (use for wipe/clockWipe)
linearTiming({ durationInFrames: 18 })
```

### Transition density rules

- **Hard cuts should be 50-70% of all scene changes** in fast-paced content (no transition between sequences).
- Max **2-3 distinct transition types** per video. More looks chaotic.
- Same transition type for same narrative purpose (all topic progressions use fade, all reveals use wipe).
- Never put transitions between every scene. Silence (hard cuts) creates rhythm.

---

## 6. useTransitionProgress() Pattern

Scenes can react to transitions in progress. Use this for parallax, blur, or zoom effects during scene enter/exit.

```tsx
import { useTransitionProgress } from "@remotion/transitions";
import { AbsoluteFill } from "remotion";

export const ReactiveScene: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { entering, exiting } = useTransitionProgress();

  // Blur increases as scene exits
  const blur = exiting * 8;
  // Slight zoom-out on exit
  const scale = 1 + exiting * 0.1;
  // Parallax: shift content up as scene enters from bottom
  const translateY = (1 - entering) * 40;

  return (
    <AbsoluteFill
      style={{
        filter: `blur(${blur}px)`,
        transform: `scale(${scale}) translateY(${translateY}px)`,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};
```

**Values:**
- `entering`: `0` at start of enter transition, `1` when fully entered. Always `1` when no transition active.
- `exiting`: `0` when scene is fully visible, `1` at end of exit transition. Always `0` when no transition active.

**Pair with `none()` for fully custom transitions:**

```tsx
import { none } from "@remotion/transitions/none";

<TransitionSeries.Transition
  presentation={none()}
  timing={linearTiming({ durationInFrames: 20 })}
/>
```

Both scenes render simultaneously. Use `useTransitionProgress()` inside each scene to drive any visual effect.

---

## 7. MainVideo.tsx Template

Full example: 6-scene YouTube Short with `TransitionSeries`, audio, and narrative-mapped transitions.

```tsx
// src/MainVideo.tsx
import React from "react";
import { AbsoluteFill, Audio, staticFile } from "remotion";
import { TransitionSeries, linearTiming, springTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { slide } from "@remotion/transitions/slide";
import { wipe } from "@remotion/transitions/wipe";
import { HookScene } from "./scenes/HookScene";
import { ProblemScene } from "./scenes/ProblemScene";
import { SolutionScene } from "./scenes/SolutionScene";
import { DemoScene } from "./scenes/DemoScene";
import { ResultScene } from "./scenes/ResultScene";
import { OutroScene } from "./scenes/OutroScene";
import { TIMING } from "./timing";

// Transition durations (frames)
const T = {
  hookEntry: 12,
  topicFade: 15,
  revealWipe: 18,
  energyPunch: 15,
  closeFade: 24,
} as const;

// Total duration accounting for transition overlap:
// sum(scene durations) - sum(transition durations)
const TOTAL_DURATION =
  TIMING.hook +
  TIMING.problem +
  TIMING.solution +
  TIMING.demo +
  TIMING.result +
  TIMING.outro -
  T.hookEntry -
  T.topicFade -
  T.revealWipe -
  T.energyPunch -
  T.closeFade;

export const MainVideo: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#0A0A0A" }}>
      {/* Background music — sits outside TransitionSeries */}
      <Audio src={staticFile("audio/bgmusic.mp3")} volume={0.12} />

      <TransitionSeries>
        {/* Scene 1: Hook */}
        <TransitionSeries.Sequence durationInFrames={TIMING.hook}>
          <HookScene />
          <Audio src={staticFile("audio/beat-hook.mp3")} volume={0.8} />
        </TransitionSeries.Sequence>

        {/* Transition: slide from bottom (hook entry) */}
        <TransitionSeries.Transition
          presentation={slide({ direction: "from-bottom" })}
          timing={springTiming({ config: { damping: 200 }, durationInFrames: T.hookEntry })}
        />

        {/* Scene 2: Problem */}
        <TransitionSeries.Sequence durationInFrames={TIMING.problem}>
          <ProblemScene />
          <Audio src={staticFile("audio/beat-problem.mp3")} volume={0.8} />
        </TransitionSeries.Sequence>

        {/* Transition: fade (topic progression) */}
        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: T.topicFade })}
        />

        {/* Scene 3: Solution */}
        <TransitionSeries.Sequence durationInFrames={TIMING.solution}>
          <SolutionScene />
          <Audio src={staticFile("audio/beat-solution.mp3")} volume={0.8} />
        </TransitionSeries.Sequence>

        {/* Transition: wipe (reveal) */}
        <TransitionSeries.Transition
          presentation={wipe({ direction: "from-left" })}
          timing={linearTiming({ durationInFrames: T.revealWipe })}
        />

        {/* Scene 4: Demo */}
        <TransitionSeries.Sequence durationInFrames={TIMING.demo}>
          <DemoScene />
          <Audio src={staticFile("audio/beat-demo.mp3")} volume={0.8} />
        </TransitionSeries.Sequence>

        {/* No transition here — hard cut for pacing */}

        {/* Scene 5: Result */}
        <TransitionSeries.Sequence durationInFrames={TIMING.result}>
          <ResultScene />
          <Audio src={staticFile("audio/beat-result.mp3")} volume={0.8} />
        </TransitionSeries.Sequence>

        {/* Transition: fade (calm close) */}
        <TransitionSeries.Transition
          presentation={fade()}
          timing={linearTiming({ durationInFrames: T.closeFade })}
        />

        {/* Scene 6: Outro */}
        <TransitionSeries.Sequence durationInFrames={TIMING.outro}>
          <OutroScene />
          <Audio src={staticFile("audio/beat-outro.mp3")} volume={0.6} />
        </TransitionSeries.Sequence>
      </TransitionSeries>
    </AbsoluteFill>
  );
};
```

### Companion timing.ts

```tsx
// src/timing.ts
export const TIMING = {
  hook: 90,      // 3.0s
  problem: 120,  // 4.0s
  solution: 120, // 4.0s
  demo: 150,     // 5.0s
  result: 90,    // 3.0s
  outro: 75,     // 2.5s
} as const;
```

---

## 8. Audio Integration with TransitionSeries

Audio placement inside `TransitionSeries` follows these rules:

1. **Each `<Audio>` inside a `TransitionSeries.Sequence` starts when that Sequence starts** on the timeline (accounting for transition overlap).
2. **Background music goes outside `TransitionSeries`** so it plays continuously without being affected by sequence timing.
3. **During a transition, both adjacent sequences are rendering simultaneously.** Both sequences' audio tracks play at the same time during overlap.

### Correct pattern: audio inside each sequence

```tsx
<TransitionSeries>
  <TransitionSeries.Sequence durationInFrames={90}>
    <SceneA />
    {/* This audio starts at frame 0 */}
    <Audio src={staticFile("audio/vo-scene-a.mp3")} volume={1} />
  </TransitionSeries.Sequence>

  <TransitionSeries.Transition
    presentation={fade()}
    timing={linearTiming({ durationInFrames: 15 })}
  />

  <TransitionSeries.Sequence durationInFrames={90}>
    <SceneB />
    {/* This audio starts at frame 75 (90 - 15 overlap) on the global timeline */}
    <Audio src={staticFile("audio/vo-scene-b.mp3")} volume={1} />
  </TransitionSeries.Sequence>
</TransitionSeries>
```

### Voiceover with transition-aware volume

Fade voiceover down during exit, fade up during entry to avoid two voiceovers clashing in the overlap window:

```tsx
import { useTransitionProgress } from "@remotion/transitions";
import { Audio, staticFile, interpolate } from "remotion";

export const SceneWithVO: React.FC<{ voFile: string; children: React.ReactNode }> = ({
  voFile,
  children,
}) => {
  const { entering, exiting } = useTransitionProgress();

  // Fade audio: full volume when scene is stable, duck during transitions
  const voVolume = Math.min(entering, 1 - exiting);

  return (
    <>
      {children}
      <Audio src={staticFile(voFile)} volume={voVolume} />
    </>
  );
};
```

### Background music: outside TransitionSeries

```tsx
export const MainVideo: React.FC = () => {
  return (
    <AbsoluteFill>
      {/* BGM is independent of scene transitions */}
      <Audio src={staticFile("audio/bgmusic.mp3")} volume={0.12} />

      <TransitionSeries>
        <TransitionSeries.Sequence durationInFrames={90}>
          <SceneA />
        </TransitionSeries.Sequence>
        {/* ... transitions and more scenes ... */}
      </TransitionSeries>
    </AbsoluteFill>
  );
};
```

### SFX on transition beats

Place a sound effect at the exact transition moment by putting it in the earlier sequence, timed to its end:

```tsx
<TransitionSeries.Sequence durationInFrames={90}>
  <SceneA />
  {/* Whoosh plays at the last 10 frames of SceneA = right as transition starts */}
  <Audio
    src={staticFile("audio/sfx-whoosh.mp3")}
    volume={0.6}
    startFrom={0}
    endAt={20}
  />
</TransitionSeries.Sequence>

<TransitionSeries.Transition
  presentation={slide({ direction: "from-right" })}
  timing={linearTiming({ durationInFrames: 15 })}
/>
```

To place the SFX at the right time, use a `<Sequence>` inside the `TransitionSeries.Sequence`:

```tsx
import { Sequence } from "remotion";

<TransitionSeries.Sequence durationInFrames={90}>
  <SceneA />
  {/* SFX starts 10 frames before the scene ends */}
  <Sequence from={80}>
    <Audio src={staticFile("audio/sfx-whoosh.mp3")} volume={0.6} />
  </Sequence>
</TransitionSeries.Sequence>
```
