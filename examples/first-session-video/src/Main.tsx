import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile} from 'remotion';
import {TerminalScene} from './components/TerminalScene';
import {Intro} from './scenes/Intro';
import {Outro} from './scenes/Outro';

const FPS = 30;

// Compacted cast: 70.23s (gap-capped from the original 184s).
const INTRO_FRAMES = 105; // 3.5s
const CAST_FRAMES = 2107; // 70.23s @ 30fps, rounded down
const OUTRO_FRAMES = 188; // 6.3s — beat8 (3.6s) + breathing

export const TOTAL_FRAMES = INTRO_FRAMES + CAST_FRAMES + OUTRO_FRAMES;

// Beat → composition frame. Each beat is anchored to the moment its
// content lands on screen in the compacted cast (see compacted scene-index:
// prompt-1 starts at 5.77s, prompt-2 at 30.39s, terminal ends at 70.23s).
const BEAT_FRAME = {
  beat1: 0,    // intro card
  beat2: 120,  // ~0.5s into terminal — cd-repo + claude launch
  beat3: 360,  // ~8.5s — prompt-1 typing in
  beat4: 470,  // ~12s — first git show calls firing
  beat5: 825,  // ~24s — three-commit summary visible
  beat6: 1020, // ~30.5s — prompt-2 starts
  beat7: 1620, // ~50.5s — bug-attribution answer visible
  beat8: 2240, // outro card
} as const;

const beat = (id: keyof typeof BEAT_FRAME) => (
  <Sequence from={BEAT_FRAME[id]}>
    <Audio src={staticFile(`vo/${id}.mp3`)} />
  </Sequence>
);

export const Main: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: '#1e1e2e'}}>
    {/* Intro card */}
    <Sequence from={0} durationInFrames={INTRO_FRAMES}>
      <Intro />
    </Sequence>

    {/* Terminal playback */}
    <Sequence from={INTRO_FRAMES} durationInFrames={CAST_FRAMES}>
      <TerminalScene
        castUrl={staticFile('first-session.cast')}
        sceneIndexUrl={staticFile('first-session.scene-index.json')}
      />
    </Sequence>

    {/* Outro card */}
    <Sequence from={INTRO_FRAMES + CAST_FRAMES} durationInFrames={OUTRO_FRAMES}>
      <Outro />
    </Sequence>

    {/* Audio beats — continuous walkthrough timed to on-screen events */}
    {beat('beat1')}
    {beat('beat2')}
    {beat('beat3')}
    {beat('beat4')}
    {beat('beat5')}
    {beat('beat6')}
    {beat('beat7')}
    {beat('beat8')}
  </AbsoluteFill>
);
