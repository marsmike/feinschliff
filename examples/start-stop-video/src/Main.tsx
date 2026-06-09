import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {TerminalScene, ZoomConfig} from './components/TerminalScene';
import {Intro} from './scenes/Intro';
import {Outro} from './scenes/Outro';
import {Caption} from './scenes/Caption';

// Lifted from public/start-stop.scene-index.json — hardcoded so the demo
// doesn't need a JSON loader (regenerate by re-recording then editing here).
const SCENE_INDEX = {
  steps: [
    {id: 'show-shell',      start_s: 0.715,  end_s: 1.43},
    {id: 'launch',          start_s: 1.43,   end_s: 8.303},
    {id: 'wait-for-banner', start_s: 8.303,  end_s: 19.087},
    {id: 'settle',          start_s: 19.087, end_s: 20.336},
    {id: 'ask',             start_s: 20.336, end_s: 28.932},
    {id: 'stop',            start_s: 28.932, end_s: 33.653},
    {id: 'back-to-shell',   start_s: 33.653, end_s: 34.725},
  ],
};

// ── Composition layout ──────────────────────────────────────────────────────
//
// Frame ranges (30fps). Scene durations were re-timed to fit Rob's voiceover
// from public/vo/*.mp3 (5.9s + 8.9s + 7.3s + 8.3s + 3.6s) plus a small
// breathing buffer per scene.
//
// 0–195      Intro    (6.5s) — "Two buttons. Start. Stop. Try not to embarrass yourself."
// 195–480    Scene 1  (9.5s) — launch pane + "Right, so. Open a terminal. Type c-l-a-u-d-e..."
// 480–720    Scene 2  (8.0s) — animated zoom on input + "Ask it whatever you fancy..."
// 720–990    Scene 3  (9.0s) — /exit + back to shell + "Done with it? Slash, exit..."
// 990–1125   Outro    (4.5s) — CTA + "And that's that. Now stop watching me, go build something."

const FPS = 30;

const INTRO_FRAMES   = 195;
const SCENE1_FRAMES  = 285;
const SCENE2_FRAMES  = 240;
const SCENE3_FRAMES  = 270;
const OUTRO_FRAMES   = 135;

export const TOTAL_FRAMES =
  INTRO_FRAMES + SCENE1_FRAMES + SCENE2_FRAMES + SCENE3_FRAMES + OUTRO_FRAMES;

// Step lookups from the scene index — frame-accurate cast timestamps.
const stepStart = (id: string) => {
  const s = SCENE_INDEX.steps.find((x) => x.id === id);
  if (!s) throw new Error(`step ${id} not in scene-index`);
  return s.start_s;
};

const CAST = staticFile('start-stop.cast');

// ── Sub-component: terminal scene with animated zoom ─────────────────────────

/**
 * Scene 2 (interaction) zooms into the input prompt as the user types.
 * The pane is 100 cols × 28 rows, fontSize=24 → cell ≈ 14×29 px.
 * Input prompt sits near the bottom, around row 25, col 0.
 */
const InteractionWithZoom: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Stage A (0–60 frames): static at 1.0x — viewer sees Claude's banner area.
  // Stage B (60–120):       animate scale 1.0 → 1.6, focus down to input row.
  // Stage C (120–210):      hold zoomed-in while the question types out.
  // Stage D (210–240):      animate back out to 1.0x as Claude starts answering.
  const scale = interpolate(
    frame,
    [60, 120, 210, 240],
    [1.0, 1.6, 1.6, 1.0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );
  // Focal point: row 24 = input chevron row, col 0
  const focalRow = interpolate(
    frame,
    [60, 120, 210, 240],
    [10, 23, 23, 10],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const zoom: ZoomConfig = {scale, row: focalRow, col: 0};

  return (
    <TerminalScene
      castUrl={CAST}
      // Start ~1s before the "ask" step so the viewer sees the response area first.
      startSeconds={Math.max(0, stepStart('ask') - 1)}
      fontSize={24}
      zoom={zoom}
      vignette
    />
  );
};

// ── Connector helper: two scenes share a smooth fade between them ────────────

const FadeOverlay: React.FC<{from: number; to: number; color?: string}> = ({
  from,
  to,
  color = '#11111b',
}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [from, to], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return (
    <AbsoluteFill style={{backgroundColor: color, opacity, pointerEvents: 'none'}} />
  );
};

// ── Main ─────────────────────────────────────────────────────────────────────

export const Main: React.FC = () => {
  return (
    <AbsoluteFill style={{backgroundColor: '#11111b'}}>
      {/* Intro */}
      <Sequence from={0} durationInFrames={INTRO_FRAMES}>
        <Intro
          title="Claude Code: Start & Stop"
          subtitle="Narrated by Rob"
        />
        <Audio src={staticFile('vo/intro.mp3')} volume={1} />
      </Sequence>

      {/* Scene 1 — launch */}
      <Sequence
        from={INTRO_FRAMES}
        durationInFrames={SCENE1_FRAMES}
        name="scene1-launch"
      >
        <TerminalScene
          castUrl={CAST}
          // Start a touch before the launch step so viewer sees the bash prompt first.
          startSeconds={Math.max(0, stepStart('launch') - 0.5)}
          fontSize={26}
          vignette
        />
        <Caption text="Type `claude` to start Claude Code" enterAt={20} exitAt={SCENE1_FRAMES - 10} />
        {/* Small offset so the visual loads before Rob speaks */}
        <Audio src={staticFile('vo/launch.mp3')} volume={1} />
        <FadeOverlay from={SCENE1_FRAMES - 15} to={SCENE1_FRAMES} />
      </Sequence>

      {/* Scene 2 — interaction with zoom on the input field */}
      <Sequence
        from={INTRO_FRAMES + SCENE1_FRAMES}
        durationInFrames={SCENE2_FRAMES}
        name="scene2-zoom"
      >
        <InteractionWithZoom />
        <Caption text="Zoom: watch the input field as the question types" enterAt={20} exitAt={SCENE2_FRAMES - 10} />
        <Audio src={staticFile('vo/zoom.mp3')} volume={1} />
        <FadeOverlay from={SCENE2_FRAMES - 15} to={SCENE2_FRAMES} />
      </Sequence>

      {/* Scene 3 — stop */}
      <Sequence
        from={INTRO_FRAMES + SCENE1_FRAMES + SCENE2_FRAMES}
        durationInFrames={SCENE3_FRAMES}
        name="scene3-stop"
      >
        <TerminalScene
          castUrl={CAST}
          // Start at the "stop" step (typing /exit).
          startSeconds={Math.max(0, stepStart('stop') - 0.3)}
          fontSize={26}
          vignette
        />
        <Caption text="`/exit` returns you to your shell" enterAt={20} exitAt={SCENE3_FRAMES - 10} />
        <Audio src={staticFile('vo/stop.mp3')} volume={1} />
        <FadeOverlay from={SCENE3_FRAMES - 15} to={SCENE3_FRAMES} />
      </Sequence>

      {/* Outro */}
      <Sequence
        from={INTRO_FRAMES + SCENE1_FRAMES + SCENE2_FRAMES + SCENE3_FRAMES}
        durationInFrames={OUTRO_FRAMES}
      >
        <Outro message="That's how you start and stop." cta="claude" />
        <Audio src={staticFile('vo/outro.mp3')} volume={1} />
      </Sequence>
    </AbsoluteFill>
  );
};
