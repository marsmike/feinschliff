import React from 'react';
import {Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Beat, Theme} from '../theme';
import {CLAMP, withAlpha} from './util';

// image_card — OVERLAY: a frosted card pinned to the bottom ~48% of the
// frame. The speaker stays visible above it (invariant 3: overlays never
// replace the frame), so there is no backdrop fill here.
export const ImageCard: React.FC<{beat: Beat; theme: Theme}> = ({beat, theme}) => {
  const frame = useCurrentFrame();
  const {width} = useVideoConfig();

  // Plans come from an LLM — coerce instead of trusting the string type.
  // image_path is a bare staged filename relative to edit-engine/public/
  // (the Python render stage hardlinks assets there), or an http(s) URL —
  // same resolution contract as EditedVideo's `source`.
  const imagePath = String(beat.image_path ?? '');
  const caption = String(beat.caption ?? '');
  const src = imagePath
    ? (/^https?:\/\//.test(imagePath) ? imagePath : staticFile(imagePath))
    : null;

  // `vertical` is intentionally ignored: the card is geometry-locked to the
  // bottom band so the speaker's face zone stays clear regardless of plan.

  // Generic fallback keeps arbitrary brand stacks degrading to sans, never serif.
  const bodyFamily = `${theme.fontBody}, sans-serif`;

  // Entrance: slide up 24px + fade over 9 frames. Frame counts assume
  // fps=30 (props.py pins it).
  const cardOpacity = interpolate(frame, [0, 9], [0, 1], CLAMP);
  const cardY = interpolate(frame, [0, 9], [24, 0], CLAMP);

  return (
    // Frosted card — surface at ~0.92 alpha over a 14px backdrop blur. The
    // accent border is the ONE theme.accent element in this template.
    <div
      style={{
        position: 'absolute',
        bottom: '4%',
        left: '6%', // (100% − 88%) / 2 — horizontally centered
        width: '88%',
        height: '44%',
        borderRadius: 24,
        overflow: 'hidden', // image + caption inherit the rounded corners
        backgroundColor: withAlpha(theme.surface, 'EB'), // ~0.92 alpha
        border: `1px solid ${withAlpha(theme.accent, '40')}`, // ~0.25 alpha
        boxShadow: '0 12px 48px rgba(0,0,0,0.45)',
        backdropFilter: 'blur(14px)',
        WebkitBackdropFilter: 'blur(14px)',
        opacity: cardOpacity,
        transform: `translateY(${cardY}px)`,
      }}
    >
      {src ? (
        <Img
          src={src}
          style={{
            // The card IS the frame here — cover fills it edge to edge
            // (unlike the full-screen static takeover, where contain is
            // correct because the stage letterboxes the asset).
            width: '100%',
            height: '100%',
            objectFit: 'cover',
          }}
        />
      ) : null}
      {caption ? (
        <div
          style={{
            position: 'absolute',
            bottom: 0,
            left: 0,
            width: '100%',
            boxSizing: 'border-box',
            padding: '16px 20px',
            background: 'linear-gradient(transparent, rgba(0,0,0,0.55))',
            color: theme.text,
            fontFamily: bodyFamily,
            fontWeight: 500,
            fontSize: width * 0.026,
          }}
        >
          {caption}
        </div>
      ) : null}
    </div>
  );
};
