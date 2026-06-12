import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {measureText} from '@remotion/layout-utils';
import {Beat, Theme} from '../theme';

const CLAMP = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// stat_punch — full takeover hero number.
export const StatPunch: React.FC<{beat: Beat; theme: Theme}> = ({beat, theme}) => {
  const frame = useCurrentFrame();
  const {width} = useVideoConfig();

  // Plans come from an LLM — `value: 10` (numeric) is typical output, so
  // coerce instead of trusting the string type.
  const value = String(beat.value ?? '');
  const caption = String(beat.caption ?? '');

  // The generic fallback keeps arbitrary brand font stacks degrading to
  // sans, never the renderer's default serif.
  const titleFamily = `${theme.fontTitle}, sans-serif`;
  const bodyFamily = `${theme.fontBody}, sans-serif`;

  // Auto-fit: MEASURE the longest authored line (not the longest token — a
  // line like "$400M REVENUE" wraps otherwise) and scale so it fits ~88% of
  // frame width — never overflow (invariant 1). measureText must see the
  // exact fontFamily string the element renders with.
  const base = width * 0.32;
  const maxLineWidth = Math.max(
    1,
    ...value.split('\n').map(
      (line) =>
        measureText({text: line, fontFamily: titleFamily, fontWeight: '900', fontSize: base})
          .width,
    ),
  );
  const fontSize = base * Math.min(1, (width * 0.88) / maxLineWidth);

  // Entrance frame counts assume fps=30 (props.py pins it).
  const valueOpacity = interpolate(frame, [0, 10], [0, 1], CLAMP);
  const valueY = interpolate(frame, [0, 10], [24, 0], CLAMP);
  const captionOpacity = interpolate(frame, [8, 18], [0, 1], CLAMP);

  return (
    // Takeover backdrop is STATIC — full opacity from frame 0; only the
    // foreground animates. Prevents the speaker flickering through during
    // entrance frames (invariant 3).
    <AbsoluteFill
      style={{
        backgroundColor: theme.bg,
        justifyContent: 'center',
        alignItems: 'center',
        flexDirection: 'column',
      }}
    >
      <div
        style={{
          color: theme.accent,
          fontFamily: titleFamily,
          fontWeight: 900,
          fontSize,
          lineHeight: 1.02,
          whiteSpace: 'pre-line',
          textAlign: 'center',
          opacity: valueOpacity,
          transform: `translateY(${valueY}px)`,
        }}
      >
        {value}
      </div>
      <div
        style={{
          color: theme.muted,
          fontFamily: bodyFamily,
          fontSize: width * 0.035,
          textTransform: 'uppercase',
          letterSpacing: '0.14em',
          marginTop: 28,
          textAlign: 'center',
          opacity: captionOpacity,
        }}
      >
        {caption}
      </div>
    </AbsoluteFill>
  );
};
