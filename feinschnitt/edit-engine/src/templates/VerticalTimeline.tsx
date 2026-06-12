import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Beat, Theme} from '../theme';

const CLAMP = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

const DOT_SIZE = 14;
const RAIL_WIDTH = 3;
const CONTENT_GAP = 24; // px between the rail and the heading column
// The rail starts rising from the title area this many frames before the
// first step's appearFrame (~0.4s — frame counts assume fps=30).
const RAIL_LEAD_FRAMES = 12;

// vertical_timeline — full takeover, sequence kind: an accent rail grows
// downward and "delivers" each step's dot exactly when its appear_sec hits.
export const VerticalTimeline: React.FC<{beat: Beat; theme: Theme}> = ({beat, theme}) => {
  const frame = useCurrentFrame(); // relative to this beat's Sequence
  const {width, height, fps} = useVideoConfig();

  // Plans come from an LLM — coerce instead of trusting types (invariant 1).
  const title = String(beat.title ?? '');
  // Generic fallback keeps arbitrary brand stacks degrading to sans, never serif.
  const titleFamily = `${theme.fontTitle}, sans-serif`;
  const bodyFamily = `${theme.fontBody}, sans-serif`;

  // appear_sec is ABSOLUTE source-video seconds; the Sequence `from` is
  // Math.round(beat.start_sec * fps), so use the SAME rounding here for
  // frame-exact step offsets (invariant 2).
  const beatStartFrame = Math.round(Number(beat.start_sec) * fps);
  const steps = (Array.isArray(beat.steps) ? beat.steps : [])
    .filter((s): s is Record<string, unknown> => typeof s === 'object' && s !== null)
    .map((s) => ({
      heading: String(s.heading ?? ''),
      description: String(s.description ?? ''),
      appearFrame: Math.round(Number(s.appear_sec ?? 0) * fps) - beatStartFrame,
    }));

  // Geometry — FIXED row height so every dot's Y is deterministic (the rail
  // keyframes below depend on it). Column spans 18%..92% of frame height.
  const railX = width * 0.18;
  const headingSize = width * 0.034;
  const headingLineH = headingSize * 1.25;
  const columnTop = height * 0.18; // below the title block
  const available = height * 0.74;
  const rowH = steps.length > 0 ? Math.min(height * 0.15, available / steps.length) : 0;
  const rows = steps.map((step, i) => ({
    ...step,
    rowTop: columnTop + i * rowH,
    dotY: columnTop + i * rowH + headingLineH / 2, // dot centered on heading line 1
  }));

  // THE RAIL DRIVES THE DOTS: the rail head's Y is a piecewise-linear
  // interpolation through the keyframes (appearFrame_i, dotY_i) — so the
  // head reaches dot i exactly on the frame the dot pops, by construction.
  // A lead keyframe makes the rail rise out of the title area before step 0.
  //
  // interpolate() requires a STRICTLY monotonically increasing input range,
  // but lint does NOT enforce strictly increasing appear_secs across steps —
  // two steps may share an appear_sec (or arrive out of order). Sort the
  // keyframes ascending and bump any non-increasing frame by +1 so
  // interpolate never throws; run a running-max over the outputs so the
  // rail head never retreats (monotonic non-decreasing).
  const railTop = columnTop - height * 0.04;
  const inFrames: number[] = [];
  const outYs: number[] = [];
  const sorted = rows.map((r) => ({f: r.appearFrame, y: r.dotY})).sort((a, b) => a.f - b.f);
  if (sorted.length > 0) {
    inFrames.push(sorted[0].f - RAIL_LEAD_FRAMES);
    outYs.push(railTop);
    for (const kf of sorted) {
      const prevF = inFrames[inFrames.length - 1];
      inFrames.push(kf.f > prevF ? kf.f : prevF + 1);
      outYs.push(Math.max(outYs[outYs.length - 1], kf.y));
    }
  }
  const headY = inFrames.length >= 2 ? interpolate(frame, inFrames, outYs, CLAMP) : railTop;

  return (
    // Takeover backdrop is STATIC — full opacity from frame 0; only the
    // foreground animates. Prevents the speaker flickering through during
    // entrance frames (invariant 3).
    <AbsoluteFill style={{backgroundColor: theme.bg}}>
      {title ? (
        <div
          style={{
            position: 'absolute',
            top: height * 0.08,
            left: 0,
            width: '100%',
            textAlign: 'center',
            color: theme.text,
            fontFamily: titleFamily,
            fontWeight: 700,
            fontSize: width * 0.045,
          }}
        >
          {title}
        </div>
      ) : null}
      {/* Rail + dots are theme.accent — acceptable plural: the rail IS the
          accent motif. No OTHER element in this template uses accent. */}
      <div
        style={{
          position: 'absolute',
          left: railX - RAIL_WIDTH / 2,
          top: railTop,
          width: RAIL_WIDTH,
          height: Math.max(0, headY - railTop),
          backgroundColor: theme.accent,
          borderRadius: RAIL_WIDTH / 2,
        }}
      />
      {rows.map((row, i) => {
        // Negative offsets happen when alignment shifts the beat start past
        // an authored appear_sec; clamp so the step still gets its entrance.
        // Entrance frame counts assume fps=30 (props.py pins it).
        const af = Math.max(0, row.appearFrame);
        const dotScale = interpolate(frame, [af, af + 5], [0, 1], CLAMP);
        const textOpacity = interpolate(frame, [af, af + 6], [0, 1], CLAMP);
        return (
          <React.Fragment key={i}>
            <div
              style={{
                position: 'absolute',
                left: railX - DOT_SIZE / 2,
                top: row.dotY - DOT_SIZE / 2,
                width: DOT_SIZE,
                height: DOT_SIZE,
                borderRadius: '50%',
                backgroundColor: theme.accent,
                transform: `scale(${dotScale})`,
              }}
            />
            <div
              style={{
                position: 'absolute',
                left: railX + CONTENT_GAP,
                right: width * 0.08,
                top: row.rowTop,
                color: theme.text,
                fontFamily: titleFamily,
                fontWeight: 700,
                fontSize: headingSize,
                lineHeight: 1.25,
                whiteSpace: 'nowrap', // one line each — ellipsize overflow
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                opacity: textOpacity,
              }}
            >
              {row.heading}
            </div>
            {row.description ? (
              <div
                style={{
                  position: 'absolute',
                  left: railX + CONTENT_GAP,
                  right: width * 0.08,
                  top: row.rowTop + headingLineH + 8,
                  color: theme.muted,
                  fontFamily: bodyFamily,
                  fontSize: width * 0.026,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  opacity: textOpacity, // fades with its heading
                }}
              >
                {row.description}
              </div>
            ) : null}
          </React.Fragment>
        );
      })}
    </AbsoluteFill>
  );
};
