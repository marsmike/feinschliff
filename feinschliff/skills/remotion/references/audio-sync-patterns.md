# Audio Sync Patterns

Patterns for synchronizing Remotion animations with voiceover audio.

## Per-Beat Audio (Recommended)

Each beat has its own audio file placed inside its `<Sequence>`. This prevents clipping and ensures each beat's VO plays for exactly its duration:

```tsx
import { Sequence, Audio, AbsoluteFill } from "remotion";
import { staticFile } from "remotion";
import { timing } from "./timing";

export const MainComposition: React.FC = () => {
  return (
    <AbsoluteFill>
      {timing.scenes.map(scene =>
        scene.beats.map(beat => (
          <Sequence
            key={beat.id}
            from={beat.startFrame}
            durationInFrames={beat.endFrame - beat.startFrame}
          >
            <Audio src={staticFile(beat.audioFile)} />
            <BeatComponent beatId={beat.id} />
          </Sequence>
        ))
      )}
    </AbsoluteFill>
  );
};
```

**Critical:** The beat's `durationInFrames` must be >= the audio file's duration in frames. If the audio is 2.9 seconds and fps is 30, the beat needs at least 87 frames. Always measure with `ffprobe` and add padding.

## Single Audio File (Legacy)

If using one monolithic audio file, place `<Audio>` at the composition root (outside any `<Sequence>`):

```tsx
<AbsoluteFill>
  <Audio src={staticFile("voiceover.mp3")} />
  {/* Sequences here */}
</AbsoluteFill>
```

**Warning:** This approach makes it hard to sync individual beats and risks clipping if timing is off. Prefer per-beat audio.

## Scene-Level Composition

Group beats into scene compositions for better organization:

```tsx
export const SceneComposition: React.FC<{ sceneId: string }> = ({ sceneId }) => {
  const scene = getScene(sceneId)!;

  return (
    <AbsoluteFill>
      {scene.beats.map(beat => (
        <Sequence
          key={beat.id}
          from={beat.startFrame - scene.startFrame}
          durationInFrames={beat.endFrame - beat.startFrame}
        >
          <BeatComponent beatId={beat.id} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
```

## Animation Timing Within a Beat

Use `useCurrentFrame()` within a beat to animate relative to the beat's start:

```tsx
const BeatComponent: React.FC<{ beatId: string }> = ({ beatId }) => {
  const frame = useCurrentFrame(); // Resets to 0 within each Sequence
  const { fps } = useVideoConfig();
  const beat = getBeat(beatId)!;
  const beatDuration = beat.endFrame - beat.startFrame;

  // Animate items with stagger relative to beat start
  const item1Opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const item2Opacity = interpolate(frame, [10, 25], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill>
      <div style={{ opacity: item1Opacity }}>First element</div>
      <div style={{ opacity: item2Opacity }}>Second element</div>
    </AbsoluteFill>
  );
};
```

## Transitions Between Scenes

Use `@remotion/transitions` for scene boundaries:

```tsx
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";

export const MainComposition: React.FC = () => {
  return (
    <AbsoluteFill>
      <Audio src={staticFile(timing.audioFile)} />

      <TransitionSeries>
        {timing.scenes.map((scene, i) => (
          <React.Fragment key={scene.id}>
            <TransitionSeries.Sequence
              durationInFrames={scene.endFrame - scene.startFrame}
            >
              <SceneComposition sceneId={scene.id} />
            </TransitionSeries.Sequence>

            {i < timing.scenes.length - 1 && (
              <TransitionSeries.Transition
                presentation={fade()}
                timing={linearTiming({ durationInFrames: 15 })}
              />
            )}
          </React.Fragment>
        ))}
      </TransitionSeries>
    </AbsoluteFill>
  );
};
```
