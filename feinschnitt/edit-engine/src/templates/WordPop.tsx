import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Beat, Theme} from '../theme';

// Heavy multi-layer shadow so cardless type stays legible over the speaker.
const SHADOW = '0 4px 24px rgba(0,0,0,0.65), 0 1px 4px rgba(0,0,0,0.8)';

const CLAMP = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

type WordPopItem = {text: string; appear_sec: number; accent?: boolean};

// `{...}` span syntax: "FUTURE OF {solo business}" renders the braced span in
// theme.accent (braces stripped).
const renderSpans = (text: string, theme: Theme): React.ReactNode =>
  text.split(/(\{[^}]*\})/).map((part, i) =>
    part.startsWith('{') && part.endsWith('}') ? (
      <span key={i} style={{color: theme.accent}}>
        {part.slice(1, -1)}
      </span>
    ) : (
      <React.Fragment key={i}>{part}</React.Fragment>
    ),
  );

// word_pop — cardless typography over the speaker, one item at a time.
export const WordPop: React.FC<{beat: Beat; theme: Theme}> = ({beat, theme}) => {
  const frame = useCurrentFrame(); // relative to this beat's Sequence
  const {width, height, fps} = useVideoConfig();

  const items = (beat.items as WordPopItem[] | undefined) ?? [];
  // Props assembly injects defaults, but fall back for Studio/Showcase use.
  const vertical = (beat.vertical as number | undefined) ?? 0.72;
  const size = (beat.size as number | undefined) ?? 0.085;

  // appear_sec is ABSOLUTE source-video seconds; the Sequence `from` is
  // Math.round(beat.start_sec * fps), so use the SAME rounding here for
  // frame-exact item offsets (invariant 2). Sort by offset — plans may list
  // items out of order, and an unsorted scan would let an early item shadow
  // every later one.
  const beatStartFrame = Math.round(beat.start_sec * fps);
  const timeline = items
    .map((item) => ({item, offset: Math.round(item.appear_sec * fps) - beatStartFrame}))
    .sort((a, b) => a.offset - b.offset);

  // Item i shows from its offset until item i+1's offset (last → end of beat).
  let active = -1;
  for (let i = 0; i < timeline.length; i++) {
    if (frame >= timeline[i].offset) active = i;
  }
  if (active < 0) return null;

  const {item, offset} = timeline[active];
  // Negative offsets happen when alignment shifts the beat start past an
  // authored appear_sec; clamp so the item still gets its entrance instead
  // of hard-popping. Entrance frame counts assume fps=30 (props.py pins it).
  const t = frame - Math.max(0, offset);
  const opacity = interpolate(t, [0, 7], [0, 1], CLAMP);
  const scale = interpolate(t, [0, 7], [0.92, 1], CLAMP);

  return (
    <div
      style={{
        position: 'absolute',
        top: height * vertical,
        left: 0,
        width: '100%',
        textAlign: 'center',
        // Generic fallback: arbitrary brand stacks degrade to sans, never serif.
        fontFamily: `${theme.fontTitle}, sans-serif`,
        fontWeight: 800,
        fontSize: width * size,
        textTransform: 'uppercase',
        color: item.accent ? theme.accent : theme.text,
        textShadow: SHADOW,
        opacity,
        transform: `scale(${scale})`,
      }}
    >
      {renderSpans(String(item.text ?? ''), theme)}
    </div>
  );
};
