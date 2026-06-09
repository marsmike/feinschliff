# Timing Manifest Template

Write to `src/timing.ts` in the Remotion project.

```typescript
export interface Beat {
  id: string;
  title: string;
  startFrame: number;
  endFrame: number;
  startTime: number;
  endTime: number;
  voiceover: string;
  audioFile: string; // per-beat audio file in public/, e.g. "vo-beat1-1.mp3"
}

export interface Scene {
  id: string;
  title: string;
  startFrame: number;
  endFrame: number;
  startTime: number;
  endTime: number;
  beats: Beat[];
}

export interface Timing {
  fps: number;
  totalDurationSeconds: number;
  totalFrames: number;
  audioFile: string;
  estimated: boolean;
  scenes: Scene[];
}

export const timing: Timing = {
  fps: 30,
  totalDurationSeconds: 0, // Set from audio analysis
  totalFrames: 0,          // Math.ceil(totalDurationSeconds * fps)
  audioFile: "voiceover.mp3",
  estimated: true,         // Set to false after user verifies timestamps

  scenes: [
    {
      id: "scene1",
      title: "Introduction",
      startFrame: 0,
      endFrame: 150,
      startTime: 0,
      endTime: 5,

      beats: [
        {
          id: "beat1-1",
          title: "Hook",
          startFrame: 0,
          endFrame: 60,
          startTime: 0,
          endTime: 2,
          voiceover: "Have you ever wondered..."
        },
        {
          id: "beat1-2",
          title: "Problem Statement",
          startFrame: 60,
          endFrame: 150,
          startTime: 2,
          endTime: 5,
          voiceover: "Traditional approaches fail because..."
        }
      ]
    }
    // ... more scenes
  ]
};
```

## Helper Functions

Include these in `src/timing.ts`:

```typescript
/** Get a beat by its ID */
export const getBeat = (beatId: string): Beat | undefined => {
  for (const scene of timing.scenes) {
    const beat = scene.beats.find(b => b.id === beatId);
    if (beat) return beat;
  }
  return undefined;
};

/** Get a scene by its ID */
export const getScene = (sceneId: string): Scene | undefined => {
  return timing.scenes.find(s => s.id === sceneId);
};

/** Convert seconds to frames */
export const toFrame = (seconds: number): number => {
  return Math.round(seconds * timing.fps);
};

/** Convert frames to seconds */
export const toSeconds = (frame: number): number => {
  return frame / timing.fps;
};
```
