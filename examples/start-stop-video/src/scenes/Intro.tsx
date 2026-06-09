import React from 'react';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

export const Intro: React.FC<{title: string; subtitle: string}> = ({title, subtitle}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();

  // Title: spring up + fade in
  const titleProgress = spring({frame, fps, config: {damping: 14, mass: 0.9}});
  const titleY = interpolate(titleProgress, [0, 1], [40, 0]);

  // Subtitle: enter slightly later
  const subProgress = spring({
    frame: Math.max(0, frame - 12),
    fps,
    config: {damping: 18},
  });
  const subY = interpolate(subProgress, [0, 1], [20, 0]);

  // Underline grows from left to right after title is in
  const underlineProgress = interpolate(
    frame,
    [18, 38],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  // Whole intro fades out at end (intro is 195 frames; fade between 175-195)
  const exitFade = interpolate(frame, [175, 195], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill
      style={{
        background: 'radial-gradient(ellipse at center, #1e1e2e 0%, #11111b 100%)',
        opacity: exitFade,
      }}
    >
      {/* Subtle dot grid */}
      <AbsoluteFill
        style={{
          backgroundImage:
            'radial-gradient(rgba(205,214,244,0.06) 1px, transparent 1px)',
          backgroundSize: '24px 24px',
        }}
      />

      {/* Centered title block */}
      <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center'}}>
        <div style={{textAlign: 'center', maxWidth: width * 0.8}}>
          <div
            style={{
              fontFamily: '"Inter","SF Pro Display",sans-serif',
              fontWeight: 800,
              fontSize: 96,
              color: '#cdd6f4',
              letterSpacing: -1.5,
              opacity: titleProgress,
              transform: `translateY(${titleY}px)`,
            }}
          >
            {title}
          </div>

          <div
            style={{
              height: 4,
              borderRadius: 2,
              margin: '24px auto 0',
              background: 'linear-gradient(90deg, #f38ba8 0%, #cba6f7 50%, #89b4fa 100%)',
              width: `${underlineProgress * 380}px`,
              transition: undefined,
            }}
          />

          <div
            style={{
              marginTop: 32,
              fontFamily: '"JetBrains Mono","Menlo",monospace',
              fontSize: 32,
              color: '#a6adc8',
              opacity: subProgress,
              transform: `translateY(${subY}px)`,
            }}
          >
            {subtitle}
          </div>
        </div>
      </AbsoluteFill>

      {/* Branding pip — small "cli-recorder × Remotion" mark in lower-left */}
      <div
        style={{
          position: 'absolute',
          left: 56,
          bottom: 48,
          fontFamily: '"JetBrains Mono",monospace',
          fontSize: 18,
          color: '#7f849c',
          letterSpacing: 1.2,
          opacity: titleProgress,
        }}
      >
        cli-recorder × Remotion
      </div>
    </AbsoluteFill>
  );
};
