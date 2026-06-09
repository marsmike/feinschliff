import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

export const Outro: React.FC<{message: string; cta: string}> = ({message, cta}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  const enter = spring({frame, fps, config: {damping: 14}});
  const ctaEnter = spring({frame: Math.max(0, frame - 14), fps, config: {damping: 18}});

  // Cursor blink at the end of the CTA
  const blink = Math.floor(frame / 16) % 2 === 0;

  return (
    <AbsoluteFill
      style={{
        background: 'linear-gradient(135deg, #11111b 0%, #1e1e2e 50%, #181825 100%)',
        opacity: enter,
      }}
    >
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <div style={{textAlign: 'center'}}>
          <div
            style={{
              fontFamily: '"Inter","SF Pro Display",sans-serif',
              fontWeight: 700,
              fontSize: 72,
              color: '#cdd6f4',
              letterSpacing: -1,
              transform: `translateY(${interpolate(enter, [0, 1], [40, 0])}px)`,
            }}
          >
            {message}
          </div>

          <div
            style={{
              marginTop: 40,
              padding: '24px 48px',
              fontFamily: '"JetBrains Mono",monospace',
              fontSize: 36,
              color: '#a6e3a1',
              border: '2px solid rgba(166,227,161,0.4)',
              borderRadius: 12,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 14,
              opacity: ctaEnter,
              transform: `translateY(${interpolate(ctaEnter, [0, 1], [20, 0])}px)`,
              backgroundColor: 'rgba(166,227,161,0.05)',
            }}
          >
            <span style={{color: '#89b4fa'}}>$</span>
            <span>{cta}</span>
            <span style={{opacity: blink ? 1 : 0, color: '#cdd6f4'}}>▌</span>
          </div>
        </div>
      </AbsoluteFill>

      <div
        style={{
          position: 'absolute',
          left: 56,
          bottom: 48,
          fontFamily: '"JetBrains Mono",monospace',
          fontSize: 18,
          color: '#7f849c',
          letterSpacing: 1.2,
          opacity: enter,
        }}
      >
        rendered direct from .cast — no MP4 embed
      </div>
    </AbsoluteFill>
  );
};
