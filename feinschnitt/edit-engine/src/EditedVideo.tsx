import React from 'react';
import {
  AbsoluteFill, Easing, OffthreadVideo, Sequence,
  interpolate, staticFile, useCurrentFrame, useVideoConfig,
} from 'remotion';
import {Beat, EditedVideoProps, Theme, ZoomWindow} from './theme';
import {Captions} from './templates/Captions';
import {HookTitle} from './templates/HookTitle';
import {ImageCard} from './templates/ImageCard';
import {InlineChart} from './templates/InlineChart';
import {QuotePull} from './templates/QuotePull';
import {RatioDots} from './templates/RatioDots';
import {StaticTakeover} from './templates/StaticTakeover';
import {StatPunch} from './templates/StatPunch';
import {VerticalTimeline} from './templates/VerticalTimeline';
import {WordPop} from './templates/WordPop';

// Template registry — beat.kind → component. All 9 lint-known kinds have a
// template; unknown kinds simply render nothing.
const TEMPLATES: Record<string, React.FC<{beat: Beat; theme: Theme}>> = {
  hook_title: HookTitle,
  word_pop: WordPop,
  stat_punch: StatPunch,
  quote_pull: QuotePull,
  static: StaticTakeover,
  image_card: ImageCard, // overlay — NOT in TAKEOVER_KINDS
  vertical_timeline: VerticalTimeline,
  ratio_dots: RatioDots, // overlay — NOT in TAKEOVER_KINDS
  inline_chart: InlineChart, // overlay — NOT in TAKEOVER_KINDS
};

// Takeovers replace the frame. Every new takeover kind MUST be added here
// or the speaker will flicker through transition frames between beats.
// Must equal KNOWN_KINDS − OVERLAY_KINDS in feinschnitt/src/feinschnitt/edit/lint.py.
const TAKEOVER_KINDS = new Set(['stat_punch', 'quote_pull', 'static', 'vertical_timeline']);

// Adjacent takeover beats whose gap is at most this many seconds are covered
// by ONE underlay run (closes the boundary between back-to-back takeovers).
const TAKEOVER_CHAIN_GAP_SEC = 0.6;
// The underlay starts this much before the first beat of a run and ends this
// much after the last one, hiding entrance/exit transition frames.
const TAKEOVER_PAD_SEC = 0.1;

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

// Runs of consecutive takeover beats: sort by start, chain beats whose gap is
// ≤ TAKEOVER_CHAIN_GAP_SEC, so one bg slab spans each back-to-back cluster.
const takeoverRuns = (beats: Beat[]): Array<{start: number; end: number}> => {
  const runs: Array<{start: number; end: number}> = [];
  const takeovers = beats
    .filter((b) => TAKEOVER_KINDS.has(b.kind))
    .sort((a, b) => a.start_sec - b.start_sec);
  for (const b of takeovers) {
    const last = runs[runs.length - 1];
    if (last && b.start_sec - last.end <= TAKEOVER_CHAIN_GAP_SEC) {
      last.end = Math.max(last.end, b.end_sec);
    } else {
      runs.push({start: b.start_sec, end: b.end_sec});
    }
  }
  return runs;
};

export const EditedVideo: React.FC<EditedVideoProps> = ({source, beats, zoom, theme, captions}) => {
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
      {/* Coverage underlay — one static theme.bg slab under each run of
          takeover beats, padded by TAKEOVER_PAD_SEC on both sides. Invariant:
          per-template backdrops never animate (full opacity from frame 0); the
          underlay closes the entrance/exit gaps around and between adjacent
          takeover Sequences so the speaker can never flash through. */}
      {takeoverRuns(beats).map((run, i) => {
        const from = Math.max(0, Math.round((run.start - TAKEOVER_PAD_SEC) * fps));
        const to = Math.round((run.end + TAKEOVER_PAD_SEC) * fps);
        return (
          <Sequence key={`underlay-${i}`} from={from} durationInFrames={Math.max(1, to - from)}>
            <AbsoluteFill style={{backgroundColor: theme.bg}} />
          </Sequence>
        );
      })}
      {/* Beats render ABOVE the zoom wrapper so overlays are never cropped
          by a punch-in. Do not move them inside the scaled fill.
          Overlays always paint above takeovers; without this, plan array
          order silently decided visibility. Partition beats: takeovers first,
          then overlays (non-takeovers). Each group preserves array order.
          key is the ORIGINAL index so React can reconcile stably across
          re-renders regardless of partition index. */}
      {[
        ...beats.map((beat, i) => ({beat, i})).filter(({beat}) => TAKEOVER_KINDS.has(beat.kind)),
        ...beats.map((beat, i) => ({beat, i})).filter(({beat}) => !TAKEOVER_KINDS.has(beat.kind)),
      ].map(({beat, i}) => {
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
      {/* Captions — FINAL layer, above takeovers AND overlays. Suppression
          already happened in Python (captions.py); this layer renders
          whatever it receives. */}
      <Captions chunks={captions ?? []} theme={theme} />
    </AbsoluteFill>
  );
};
