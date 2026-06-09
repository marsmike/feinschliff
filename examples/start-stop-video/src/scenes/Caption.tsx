import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

/**
 * Bottom-left chapter chip — fades in/out with the scene.
 * Use inside a <Sequence> to label what the viewer is seeing on the terminal.
 */
export const Caption: React.FC<{
  text: string;
  /** When (in scene-local frames) the caption should appear. */
  enterAt?: number;
  /** When the caption should disappear. */
  exitAt?: number;
}> = ({text, enterAt = 0, exitAt}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const enter = spring({frame: Math.max(0, frame - enterAt), fps, config: {damping: 16}});
  const exit = exitAt !== undefined
    ? interpolate(frame, [exitAt - 8, exitAt], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})
    : 1;

  const opacity = Math.min(enter, exit);

  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      <div
        style={{
          position: 'absolute',
          bottom: 64,
          left: 64,
          padding: '16px 28px',
          fontFamily: '"Inter","SF Pro Display",sans-serif',
          fontWeight: 600,
          fontSize: 28,
          color: '#cdd6f4',
          backgroundColor: 'rgba(17,17,27,0.85)',
          border: '1px solid rgba(205,214,244,0.2)',
          borderRadius: 10,
          backdropFilter: 'blur(8px)',
          opacity,
          transform: `translateY(${interpolate(enter, [0, 1], [16, 0])}px)`,
        }}
      >
        <span
          style={{
            display: 'inline-block',
            width: 10,
            height: 10,
            borderRadius: 5,
            backgroundColor: '#a6e3a1',
            marginRight: 14,
            verticalAlign: 'middle',
          }}
        />
        {text}
      </div>
    </AbsoluteFill>
  );
};
