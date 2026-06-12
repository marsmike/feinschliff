import React, {useMemo} from 'react';
import {Sequence, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {measureText} from '@remotion/layout-utils';
import {CaptionChunk, Theme} from '../theme';
import {CLAMP, SHADOW} from './util';
import {useFontsReady} from '../use-fonts-ready';

// Word-synced caption layer — renders the chunks the Python pipeline ships
// in props. Suppression already happened in Python (captions.py): this layer
// renders everything it receives, no filtering here.
//
// Accent discipline: the current-word highlight IS this layer's accent use.
// Python suppression keeps text beats (word_pop, hook_title, takeovers) and
// captions mutually exclusive in time, so accent collisions with beat
// templates are rare by construction.

// One chunk = one centered single line near the bottom of the frame.
const CaptionLine: React.FC<{chunk: CaptionChunk; from: number; theme: Theme}> = ({
  chunk,
  from,
  theme,
}) => {
  const frame = useCurrentFrame(); // chunk-local: the parent Sequence rebases it
  const {width, height, fps} = useVideoConfig();
  const fontsLoaded = useFontsReady();

  // word.s is ABSOLUTE source seconds; the Sequence `from` is
  // Math.round(chunk.s * fps), so use the SAME rounding here for frame-exact
  // word offsets (matches the WordPop convention). captions.py emits words in
  // chronological order, so "last offset ≤ frame" picks the CURRENT word:
  // active from its own offset until the next word's offset (the last word
  // holds until chunk end).
  // Note: when two words round to the same frame offset, the later word wins
  // (last-wins scan); they are <33ms apart at 30fps — visually instantaneous.
  const offsets = chunk.words.map((word) => Math.round(word.s * fps) - from);
  let current = -1;
  for (let i = 0; i < offsets.length; i++) {
    if (frame >= offsets[i]) current = i;
  }

  // Chunk entrance: fade + 10px rise over 4 frames (fps=30, props.py pins it).
  // No exit animation, no scale-bounce — captions stay calm under the beats.
  const opacity = interpolate(frame, [0, 4], [0, 1], CLAMP);
  const rise = interpolate(frame, [0, 4], [10, 0], CLAMP);

  // Auto-fit: measure the full UPPERCASED line at weight 900 (emphasis words
  // render 900 — widest case) and scale down to 92% of frame width if needed.
  // Guard behind fontsLoaded so fallback-font metrics never poison the cache.
  // delayRender in the hook holds the screenshot until fonts are ready, so
  // unmeasured (base) frames are never captured.
  // never wraps — fontSize is measured down to fit 92% width.
  const base = width * 0.042;
  const fontFamily = `${theme.fontTitle}, sans-serif`;
  const lineText = chunk.words.map((w) => String(w.w ?? '')).join(' ').toUpperCase();
  const fontSize = useMemo(() => {
    if (!fontsLoaded) return base;
    const measured = measureText({
      text: lineText,
      fontFamily,
      fontWeight: '900',
      fontSize: base,
    });
    const scale = Math.min(1, (width * 0.92) / measured.width);
    return base * scale;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fontsLoaded, lineText, fontFamily, base, width]);

  return (
    <div
      style={{
        position: 'absolute',
        top: height * 0.9,
        left: '4%',
        width: '92%',
        textAlign: 'center',
        whiteSpace: 'nowrap',
        textTransform: 'uppercase',
        // Generic fallback: arbitrary brand stacks degrade to sans, never serif.
        fontFamily,
        fontWeight: 800,
        fontSize,
        color: theme.text,
        textShadow: SHADOW,
        opacity,
        transform: `translateY(${rise}px)`,
      }}
    >
      {chunk.words.map((word, i) => {
        // Emphasis words (accent: true from the plan's emphasis phrases) stay
        // gold at weight 900 regardless of which word is current.
        const emphasized = word.accent === true;
        const isCurrent = i === current;
        return (
          <React.Fragment key={i}>
            {i > 0 ? ' ' : ''}
            <span
              style={{
                color: isCurrent || emphasized ? theme.accent : theme.text,
                fontWeight: emphasized ? 900 : 800,
              }}
            >
              {String(word.w ?? '')}
            </span>
          </React.Fragment>
        );
      })}
    </div>
  );
};

export const Captions: React.FC<{chunks: CaptionChunk[]; theme: Theme}> = ({
  chunks,
  theme,
}) => {
  const {fps} = useVideoConfig();
  return (
    <>
      {chunks.map((chunk, i) => {
        const from = Math.round(chunk.s * fps);
        const durationInFrames = Math.max(1, Math.round(chunk.e * fps) - from);
        return (
          <Sequence key={i} from={from} durationInFrames={durationInFrames}>
            <CaptionLine chunk={chunk} from={from} theme={theme} />
          </Sequence>
        );
      })}
    </>
  );
};
