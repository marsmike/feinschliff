import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Beat, Theme} from '../theme';

const CLAMP = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// static — full takeover showing a real asset (screenshot, photo, chart image).
export const StaticTakeover: React.FC<{beat: Beat; theme: Theme}> = ({beat, theme}) => {
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

  // Generic fallback keeps arbitrary brand stacks degrading to sans, never serif.
  const bodyFamily = `${theme.fontBody}, sans-serif`;

  // Entrance frame counts assume fps=30 (props.py pins it). Foreground only.
  const imgOpacity = interpolate(frame, [0, 8], [0, 1], CLAMP);
  const imgScale = interpolate(frame, [0, 8], [1.02, 1], CLAMP);
  const captionOpacity = interpolate(frame, [6, 16], [0, 1], CLAMP);

  return (
    // Takeover backdrop is STATIC — full opacity from frame 0; only the
    // foreground animates. Prevents the speaker flickering through during
    // entrance frames (invariant 3).
    <AbsoluteFill
      style={{
        backgroundColor: theme.bg,
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      {src ? (
        <Img
          src={src}
          style={{
            // Small screenshots scale up to the stage; contain never crops.
            // width/height fill the box so even tiny images expand to the
            // stage bounds; objectFit:'contain' letterboxes inside that box.
            width: '88%',
            height: '80%',
            objectFit: 'contain',
            opacity: imgOpacity,
            transform: `scale(${imgScale})`,
          }}
        />
      ) : null}
      {caption ? (
        <div
          style={{
            position: 'absolute',
            bottom: '5%',
            left: 0,
            width: '100%',
            textAlign: 'center',
            color: theme.muted,
            fontFamily: bodyFamily,
            fontSize: width * 0.028,
            textTransform: 'uppercase',
            letterSpacing: '0.14em',
            opacity: captionOpacity,
          }}
        >
          {caption}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
