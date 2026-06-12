import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Beat, Theme} from '../theme';
import {CLAMP, SHADOW} from './util';

// ratio_dots — OVERLAY: an N-of-M dot grid in the lower-mid band whose
// marked subset flips state at mark_at. The speaker stays visible around
// the block (invariant 3: overlays never replace the frame).
//
// Accent discipline: the dot grid IS the single accent motif (acceptable
// plural, same reading as VerticalTimeline's rail) — before the flip on
// "negative" polarity every dot is accent; after the flip only the
// survivors are. No OTHER element in this template uses theme.accent.
export const RatioDots: React.FC<{beat: Beat; theme: Theme}> = ({beat, theme}) => {
  const frame = useCurrentFrame(); // relative to this beat's Sequence
  const {width, height, fps} = useVideoConfig();

  // Plans come from an LLM — coerce instead of trusting types (invariant 1).
  // Lint guarantees sane values upstream, but direct-props use (Studio /
  // Showcase) must not crash: floor + clamp total into 1..100 and marked
  // into 0..total.
  const totalRaw = Math.floor(Number(beat.total));
  const total = Math.min(100, Math.max(1, Number.isFinite(totalRaw) ? totalRaw : 1));
  const markedRaw = Math.floor(Number(beat.marked));
  const marked = Math.min(total, Math.max(0, Number.isFinite(markedRaw) ? markedRaw : 0));
  const polarity = beat.polarity === 'positive' ? 'positive' : 'negative';
  const caption = String(beat.caption ?? '');

  // mark_at is ABSOLUTE source-video seconds; the Sequence `from` is
  // Math.round(beat.start_sec * fps), so use the SAME rounding here for a
  // frame-exact flip (invariant 2). A missing/NaN mark_at parks the flip
  // far in the future instead of feeding NaN into interpolate.
  const beatStartFrame = Math.round(Number(beat.start_sec) * fps);
  const markAt = Number(beat.mark_at);
  const markFrame = Number.isFinite(markAt)
    ? Math.round(markAt * fps) - beatStartFrame
    : 1e9;
  // One shared 12-frame flip ramp for the whole marked subset. Frame counts
  // assume fps=30 (props.py pins it).
  const flip = interpolate(frame, [markFrame, markFrame + 12], [0, 1], CLAMP);

  // `vertical` is intentionally ignored: the dot grid is band-locked to the
  // lower-mid zone (68% center) so the speaker's face stays clear regardless
  // of plan. Same contract as ImageCard's geometry-locked bottom band.

  // Grid geometry — block centered horizontally, vertical center at 68% of
  // frame height (lower-mid band), max width 80% of the frame.
  const cols = Math.ceil(Math.sqrt(total));
  const rows = Math.ceil(total / cols);
  const dotPx = Math.max(10, Math.min(80, ((width * 0.8) / cols) * 0.55));
  const gap = dotPx * 0.6;
  const blockW = cols * dotPx + (cols - 1) * gap;
  const blockH = rows * dotPx + (rows - 1) * gap;
  const gridLeft = (width - blockW) / 2;
  const gridTop = height * 0.68 - blockH / 2;

  // Generic fallback keeps arbitrary brand stacks degrading to sans, never serif.
  const bodyFamily = `${theme.fontBody}, sans-serif`;

  return (
    <>
      {caption ? (
        // Caption sits over the speaker — heavy shadow, anchored by its
        // BOTTOM edge one gap above the grid so wrapping grows upward.
        <div
          style={{
            position: 'absolute',
            left: '10%',
            width: '80%',
            bottom: height - gridTop + gap,
            textAlign: 'center',
            color: theme.text,
            fontFamily: bodyFamily,
            fontWeight: 600,
            fontSize: width * 0.028,
            letterSpacing: '0.14em',
            textTransform: 'uppercase',
            textShadow: SHADOW,
          }}
        >
          {caption}
        </div>
      ) : null}
      {Array.from({length: total}, (_, i) => {
        const col = i % cols;
        const row = Math.floor(i / cols);
        const x = gridLeft + col * (dotPx + gap);
        const y = gridTop + row * (dotPx + gap);
        // Entrance: each dot pops in over 3 frames. Stagger is capped so all
        // dots finish entering within ~1.5s + 3 frames regardless of total
        // (100 dots: stagger=0.45f, last dot done at frame ~48 ≈ 1.6s @30fps).
        const stagger = Math.min(2, 45 / total);
        const pop = interpolate(frame, [i * stagger, i * stagger + 3], [0, 1], CLAMP);
        // Deterministic marked subset: the LAST `marked` dots in grid order.
        const isMarked = i >= total - marked;
        const t = isMarked ? flip : 0;
        // negative: every dot starts accent; the marked subset fades to
        //   muted at 40% opacity and gains an X stroke.
        // positive: every dot starts muted at 45%; the marked subset
        //   brightens to accent with a slight scale pulse.
        const baseColor = polarity === 'negative' ? theme.accent : theme.muted;
        const baseOpacity = polarity === 'negative' ? 1 - t : 0.45 * (1 - t);
        const flipColor = polarity === 'negative' ? theme.muted : theme.accent;
        const flipOpacity = polarity === 'negative' ? 0.4 * t : t;
        // Positive pulse: 1 → 1.15 → 1 across the 12-frame flip window so
        // there is no pre-flip 1.15 artifact and the dot settles at 1.0.
        const pulse =
          polarity === 'positive' && isMarked
            ? interpolate(frame, [markFrame, markFrame + 3, markFrame + 12], [1, 1.15, 1], CLAMP)
            : 1;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: x,
              top: y,
              width: dotPx,
              height: dotPx,
              transform: `scale(${pop * pulse})`,
            }}
          >
            <div
              style={{
                position: 'absolute',
                inset: 0,
                borderRadius: '50%',
                backgroundColor: baseColor,
                opacity: baseOpacity,
              }}
            />
            <div
              style={{
                position: 'absolute',
                inset: 0,
                borderRadius: '50%',
                backgroundColor: flipColor,
                opacity: flipOpacity,
              }}
            />
            {polarity === 'negative' && isMarked ? (
              // Thin X stroke — two crossed 2px lines, theme.text at 70%,
              // fading in with the flip. Length = dotPx so the rotated
              // tips land exactly on the circle's edge.
              [45, -45].map((deg) => (
                <div
                  key={deg}
                  style={{
                    position: 'absolute',
                    left: '50%',
                    top: '50%',
                    width: dotPx,
                    height: 2,
                    backgroundColor: theme.text,
                    opacity: 0.7 * t,
                    transform: `translate(-50%, -50%) rotate(${deg}deg)`,
                  }}
                />
              ))
            ) : null}
          </div>
        );
      })}
    </>
  );
};
