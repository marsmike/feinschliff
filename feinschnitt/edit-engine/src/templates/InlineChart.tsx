import React from 'react';
import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {Beat, Theme} from '../theme';
import {CLAMP, withAlpha} from './util';

const PAD = 20; // inner card padding — title top-left, plot sides/bottom
const MAX_LABELS = 6; // cap on rendered axis labels

// inline_chart — OVERLAY: a dark-glass card (same family as ImageCard) in
// the lower band with a line chart that draws itself left→right. The
// speaker stays visible above/below the card (invariant 3).
//
// Accent discipline: the head dot riding the line is THE theme.accent
// element; the card's hairline border is the same low-alpha structural
// accent ImageCard uses — no other accent usage.
export const InlineChart: React.FC<{beat: Beat; theme: Theme}> = ({beat, theme}) => {
  const frame = useCurrentFrame(); // relative to this beat's Sequence
  const {width, height, fps} = useVideoConfig();

  // Plans come from an LLM — coerce instead of trusting types (invariant 1).
  // Lint guarantees ≥2 numeric data points upstream, but direct-props use
  // (Studio / Showcase) must not crash on garbage.
  const title = String(beat.title ?? '');
  const data = (Array.isArray(beat.data) ? beat.data : [])
    .map(Number)
    .filter((v) => Number.isFinite(v));
  const labels = Array.isArray(beat.labels) ? beat.labels.map((l) => String(l ?? '')) : [];
  const drawRaw = Number(beat.draw_duration);
  const drawDuration = Number.isFinite(drawRaw) && drawRaw > 0 ? drawRaw : 1.2;
  // `vertical` IS honored here: top edge of the card as a fraction of frame
  // height. The default (0.62) now lives in THREE places that must agree:
  // lint's DEFAULT_VERTICAL (lint.py), props.py injection (injected when
  // the plan omits `vertical`), and this in-template fallback (Studio /
  // direct-props use where props.py hasn't run). Keep it inside lint's
  // [0.58, 0.9] band.
  const verticalRaw = Number(beat.vertical);
  const vertical = Number.isFinite(verticalRaw) ? verticalRaw : 0.62;

  // Card geometry — centered, 84% wide, 26% of frame height.
  const cardW = width * 0.84;
  const cardH = height * 0.26;
  const cardLeft = (width - cardW) / 2; // 8% margins
  const cardTop = height * vertical;
  const titleSize = width * 0.024;
  const labelSize = width * 0.02;

  // Entrance: slide up 16px + fade over 8 frames (ImageCard family; frame
  // counts assume fps=30 — props.py pins it). The line starts drawing at
  // local frame 0, well inside the fade.
  const cardOpacity = interpolate(frame, [0, 8], [0, 1], CLAMP);
  const cardY = interpolate(frame, [0, 8], [16, 0], CLAMP);

  // Plot box — inside the card, below the title; labels reserve a row at
  // the bottom when present.
  const plotLeft = PAD;
  const plotW = cardW - 2 * PAD;
  const plotTop = PAD + titleSize * 1.2 + 12;
  const labelRowH = labels.length > 0 ? labelSize * 1.3 + 8 : 0;
  const plotBottom = cardH - PAD - labelRowH;
  const plotH = plotBottom - plotTop;

  // Normalize to [min, max] with 10% headroom on both sides — descending
  // data renders visibly descending because y maps value→pixel directly.
  const n = data.length;
  const lo = Math.min(...data);
  const hi = Math.max(...data);
  const span = hi - lo || 1; // flat data still renders a midline
  const yLo = lo - span * 0.1;
  const yHi = hi + span * 0.1;
  const points = data.map((v, i) => ({
    x: plotLeft + (n > 1 ? (i / (n - 1)) * plotW : plotW / 2),
    y: plotBottom - ((v - yLo) / (yHi - yLo)) * plotH,
  }));

  // Path length computed mathematically from the points (no DOM
  // measurement) so strokeDasharray/strokeDashoffset can animate the draw.
  const d = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
    .join(' ');
  const segLens: number[] = [];
  let totalLen = 0;
  for (let i = 1; i < n; i++) {
    const len = Math.hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y);
    segLens.push(len);
    totalLen += len;
  }

  // The polyline draws left→right over draw_duration secs from local frame 0.
  const progress = Math.min(1, Math.max(0, frame / (drawDuration * fps)));

  // Head dot position: the point at `progress` along the path by arc
  // length, linearly interpolated inside its segment.
  let head = points[0] ?? {x: plotLeft, y: plotBottom};
  let remaining = progress * totalLen;
  for (let i = 0; i < segLens.length; i++) {
    if (remaining <= segLens[i] || i === segLens.length - 1) {
      const f = segLens[i] > 0 ? Math.min(1, remaining / segLens[i]) : 1;
      head = {
        x: points[i].x + (points[i + 1].x - points[i].x) * f,
        y: points[i].y + (points[i + 1].y - points[i].y) * f,
      };
      break;
    }
    remaining -= segLens[i];
  }

  // Labels map 1:1 onto data indices. Render first and last always; middle
  // labels only if they fit: at most one per data point and at most
  // MAX_LABELS rendered, evenly spaced across the index range.
  const labelCount = Math.min(labels.length, n);
  const labelIdx =
    labelCount <= MAX_LABELS
      ? Array.from({length: labelCount}, (_, i) => i)
      : Array.from({length: MAX_LABELS}, (_, k) =>
          Math.round((k * (labelCount - 1)) / (MAX_LABELS - 1)),
        );

  // Generic fallback keeps arbitrary brand stacks degrading to sans, never serif.
  const bodyFamily = `${theme.fontBody}, sans-serif`;

  return (
    // Dark-glass card — surface at ~0.92 alpha over a 10px backdrop blur,
    // accent hairline border at low alpha (ImageCard family).
    <div
      style={{
        position: 'absolute',
        top: cardTop,
        left: cardLeft,
        width: cardW,
        height: cardH,
        borderRadius: 20,
        overflow: 'hidden',
        backgroundColor: withAlpha(theme.surface, 'EB'), // ~0.92 alpha
        border: `1px solid ${withAlpha(theme.accent, '40')}`, // ~0.25 alpha
        boxShadow: '0 12px 48px rgba(0,0,0,0.45)',
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
        opacity: cardOpacity,
        transform: `translateY(${cardY}px)`,
      }}
    >
      {title ? (
        <div
          style={{
            position: 'absolute',
            top: PAD,
            left: PAD,
            right: PAD,
            color: theme.muted,
            fontFamily: bodyFamily,
            fontWeight: 600,
            fontSize: titleSize,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {title}
        </div>
      ) : null}
      {n >= 2 ? (
        <svg
          width={cardW}
          height={cardH}
          viewBox={`0 0 ${cardW} ${cardH}`}
          style={{position: 'absolute', top: 0, left: 0}}
        >
          <path
            d={d}
            fill="none"
            stroke={theme.text}
            strokeWidth={3}
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeDasharray={totalLen}
            strokeDashoffset={totalLen * (1 - progress)}
          />
          {/* Accent head dot (10px) riding the tip of the drawn line. */}
          <circle cx={head.x} cy={head.y} r={5} fill={theme.accent} />
        </svg>
      ) : null}
      {n >= 2
        ? labelIdx.map((i) =>
            labels[i] ? (
              <div
                key={i}
                style={{
                  position: 'absolute',
                  top: plotBottom + 8,
                  left: points[i].x,
                  // Edge labels anchor inward (first left-aligned, last
                  // right-aligned at their data point) so the card's
                  // overflow:hidden never clips them; middles center.
                  transform: `translateX(${i === 0 ? '0%' : i === n - 1 ? '-100%' : '-50%'})`,
                  color: theme.muted,
                  fontFamily: bodyFamily,
                  fontSize: labelSize,
                  whiteSpace: 'nowrap',
                }}
              >
                {labels[i]}
              </div>
            ) : null,
          )
        : null}
    </div>
  );
};
