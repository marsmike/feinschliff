import React from 'react';
import {
  AbsoluteFill, Easing, OffthreadVideo, Sequence,
  interpolate, staticFile, useCurrentFrame, useVideoConfig,
} from 'remotion';
import {Beat, EditedVideoProps, Theme, ZoomWindow} from './theme';
import {HookTitle} from './templates/HookTitle';
import {StatPunch} from './templates/StatPunch';
import {WordPop} from './templates/WordPop';

// Template registry — beat.kind → component.
// Unknown kinds render nothing (the lint stage refuses them upstream).
const TEMPLATES: Record<string, React.FC<{beat: Beat; theme: Theme}>> = {
  hook_title: HookTitle,
  word_pop: WordPop,
  stat_punch: StatPunch,
};

const HOOK_SETTLE_SEC = 1.6; // open punched-in, ease out — never a static cold frame
const EASE = Easing.bezier(0.4, 0, 0.2, 1);
// fps-invariant ramp duration for zoom transitions
const RAMP_SEC = 0.27;

const useSpeakerScale = (zoom: ZoomWindow[]): number => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  // Cinematic hook settle: 1.12 → 1.0, cubic ease-out, one clean direction.
  let scale = t < HOOK_SETTLE_SEC ? 1 + 0.12 * Math.pow(1 - t / HOOK_SETTLE_SEC, 3) : 1;
  for (const z of zoom) {
    if (t < z.start_sec || t > z.end_sec) continue;
    const enter = interpolate(t, [z.start_sec, z.start_sec + RAMP_SEC], [0, 1],
      {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE});
    const exit = interpolate(t, [z.end_sec - RAMP_SEC, z.end_sec], [1, 0],
      {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE});
    scale = Math.max(scale, 1 + (z.scale - 1) * Math.min(enter, exit));
  }
  return scale;
};

export const EditedVideo: React.FC<EditedVideoProps> = ({source, beats, zoom, theme}) => {
  const {fps, width, height} = useVideoConfig();
  const scale = useSpeakerScale(zoom);
  // source is a FILENAME relative to edit-engine/public/ (the Python orchestrator
  // hardlinks the video there), or an http(s) URL. bare absolute paths 404 in
  // OffthreadVideo; file:// URLs are rejected; only bundle-served public/ assets work.
  const src = source
    ? (/^https?:\/\//.test(source) ? source : staticFile(source))
    : null;
  return (
    <AbsoluteFill style={{backgroundColor: theme.bg}}>
      {/* Speaker layer — the only layer the zoom transform touches. */}
      <AbsoluteFill style={{transform: `scale(${scale})`}}>
        {src ? (
          <OffthreadVideo
            src={src}
            muted
            style={{width: '100%', height: '100%', objectFit: 'cover'}}
          />
        ) : null}
      </AbsoluteFill>
      {/* Beats render ABOVE the zoom wrapper so overlays are never cropped
          by a punch-in. Do not move them inside the scaled fill. */}
      {beats.map((beat, i) => {
        const Template = TEMPLATES[beat.kind];
        if (!Template) return null;
        const from = Math.round(beat.start_sec * fps);
        const to = Math.round(beat.end_sec * fps);
        return (
          <Sequence key={i} from={from} durationInFrames={Math.max(1, to - from)}>
            <Template beat={beat} theme={theme} />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
