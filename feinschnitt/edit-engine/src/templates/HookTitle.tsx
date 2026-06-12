import React, {useMemo} from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {measureText} from '@remotion/layout-utils';
import {Beat, Theme} from '../theme';
import {useFontsReady} from '../use-fonts-ready';

// Heavy multi-layer shadow so the lockup stays legible over arbitrary video.
const SHADOW = '0 4px 24px rgba(0,0,0,0.65), 0 1px 4px rgba(0,0,0,0.8)';

const CLAMP = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// Char-count-aware TASTE scale on the longest line — short hooks stay huge,
// long ones step down. The hard never-overflow guarantee is the measured
// clamp below, not these steps.
const titleScale = (longestLine: number): number => {
  if (longestLine <= 10) return 1.0;
  if (longestLine <= 14) return 0.92;
  if (longestLine <= 18) return 0.82;
  if (longestLine <= 22) return 0.72;
  return 0.62;
};

// hook_title — composed cold-open lockup: kicker, drawn accent rule, hero title.
export const HookTitle: React.FC<{beat: Beat; theme: Theme}> = ({beat, theme}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const fontsLoaded = useFontsReady();

  // Plans come from an LLM — coerce instead of trusting the string type.
  const kicker = String(beat.kicker ?? '').trim();
  const title = String(beat.title ?? '').trim();
  // Props assembly injects the default, but fall back for Studio/Showcase use.
  const vertical = (beat.vertical as number | undefined) ?? 0.66;

  // Generic fallback so arbitrary brand stacks degrade to sans, never serif.
  const titleFamily = `${theme.fontTitle}, sans-serif`;

  const lines = title.split('\n');
  const longestLine = Math.max(1, ...lines.map((l) => l.length));
  const stepped = width * 0.13 * titleScale(longestLine);
  // MEASURE the longest line at the stepped size and clamp continuously to
  // ~88% of frame width — a 26-char German compound noun must still fit
  // (invariant 1). measureText must see the exact rendered fontFamily. Guard
  // behind fontsLoaded so we never cache a fallback-font measurement (would
  // cause inter-chunk size jumps).
  const fontSize = useMemo(() => {
    if (!fontsLoaded) return stepped; // delayRender holds the frame; this is never captured
    const maxLineWidth = Math.max(
      1,
      ...lines.map(
        (line) =>
          measureText({text: line, fontFamily: titleFamily, fontWeight: '900', fontSize: stepped})
            .width,
      ),
    );
    return stepped * Math.min(1, (width * 0.88) / maxLineWidth);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fontsLoaded, title, titleFamily, stepped, width]);

  // Entrance frame counts assume fps=30 (props.py pins it).
  const kickerOpacity = interpolate(frame, [0, 8], [0, 1], CLAMP);
  const ruleWidth = interpolate(frame, [6, 18], [0, width * 0.16], CLAMP);
  const titleOpacity = interpolate(frame, [10, 24], [0, 1], CLAMP);
  const titleBlur = interpolate(frame, [10, 24], [10, 0], CLAMP);

  return (
    <div
      style={{
        position: 'absolute',
        top: height * vertical,
        left: '4%',
        width: '92%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        textAlign: 'center',
        fontFamily: titleFamily,
      }}
    >
      {kicker ? (
        <div
          style={{
            color: theme.accent,
            fontWeight: 700,
            fontSize: width * 0.032,
            letterSpacing: '0.22em',
            // letterSpacing adds trailing tracking after the last glyph;
            // compensate so the kicker reads optically centered.
            paddingLeft: '0.22em',
            opacity: kickerOpacity,
            textShadow: SHADOW,
          }}
        >
          {kicker}
        </div>
      ) : null}
      <div
        style={{
          height: 3,
          width: ruleWidth,
          backgroundColor: theme.accent,
          margin: '14px auto',
        }}
      />
      <div
        style={{
          color: theme.text,
          fontWeight: 900,
          fontSize,
          lineHeight: 1.05,
          whiteSpace: 'pre-line',
          opacity: titleOpacity,
          filter: `blur(${titleBlur}px)`,
          textShadow: SHADOW,
        }}
      >
        {title}
      </div>
    </div>
  );
};
