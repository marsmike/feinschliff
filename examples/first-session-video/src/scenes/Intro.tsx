import React from 'react';
import {AbsoluteFill, useCurrentFrame, interpolate} from 'remotion';

export const Intro: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 12, 90, 105], [0, 1, 1, 0], {
    extrapolateRight: 'clamp',
  });
  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#1e1e2e',
        color: '#cdd6f4',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        fontFamily: '"JetBrains Mono","Menlo",monospace',
        opacity,
      }}
    >
      <div
        style={{
          fontSize: 28,
          color: '#a6adc8',
          marginBottom: 16,
          letterSpacing: 4,
          textTransform: 'uppercase',
        }}
      >
        RAISE · Claude Code · Module 3
      </div>
      <div style={{fontSize: 88, fontWeight: 700}}>First Session</div>
      <div style={{fontSize: 32, color: '#a6adc8', marginTop: 24}}>
        One turn. One follow-up. The whole loop.
      </div>
    </AbsoluteFill>
  );
};
