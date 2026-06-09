import React from 'react';
import {AbsoluteFill, useCurrentFrame, interpolate} from 'remotion';

export const Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 18, 170, 188], [0, 1, 1, 0], {
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
        Try it yourself
      </div>
      <div style={{fontSize: 60, fontWeight: 700}}>Module 3 — First Session</div>
      <div
        style={{
          fontSize: 28,
          color: '#89b4fa',
          marginTop: 24,
        }}
      >
        confluence.bsh-group.com/spaces/GENAI/pages/4399945784
      </div>
    </AbsoluteFill>
  );
};
