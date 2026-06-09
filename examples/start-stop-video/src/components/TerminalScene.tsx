/**
 * TerminalScene — render an asciicast v3 file as React-composited terminal text.
 */

import React from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useTerminalState} from './use-terminal-state';

export interface ZoomConfig {
  scale: number;
  row: number;
  col: number;
}

interface TerminalSceneProps {
  castUrl: string;
  startSeconds?: number;
  endSeconds?: number;
  fontSize?: number;
  fontFamily?: string;
  background?: string;
  zoom?: ZoomConfig;
  vignette?: boolean;
  /** Show diagnostic overlay (lines, char counts, sample text). */
  debug?: boolean;
  style?: React.CSSProperties;
}

const DEFAULT_FONT_FAMILY =
  '"JetBrains Mono","Menlo","Consolas","DejaVu Sans Mono",monospace';

const DEFAULT_BG = '#181825';

export const TerminalScene: React.FC<TerminalSceneProps> = ({
  castUrl,
  startSeconds = 0,
  endSeconds,
  fontSize = 24,
  fontFamily = DEFAULT_FONT_FAMILY,
  background = DEFAULT_BG,
  zoom,
  vignette = false,
  debug = false,
  style,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  let t = startSeconds + frame / fps;
  if (endSeconds !== undefined) t = Math.min(t, endSeconds);

  const grid = useTerminalState(castUrl, t);

  const cellWidth = fontSize * 0.6;
  const cellHeight = fontSize * 1.2;

  const transform = zoom
    ? `scale(${zoom.scale}) translate(${-zoom.col * cellWidth}px, ${-zoom.row * cellHeight}px)`
    : undefined;

  // Diagnostic counts for debug overlay.
  const nonSpaceCounts = grid.lines.map((line) =>
    line.reduce((n, c) => n + (c.char !== ' ' && c.char !== '' ? 1 : 0), 0),
  );
  const totalChars = nonSpaceCounts.reduce((a, b) => a + b, 0);
  const sampleLines = grid.lines.slice(0, 6).map((line) =>
    line.map((c) => c.char || '·').join('').slice(0, 90),
  );

  return (
    <AbsoluteFill style={{backgroundColor: background, ...style}}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          fontFamily,
          fontSize,
          lineHeight: '1.2em',
          color: '#cdd6f4',
          padding: 32,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            transform,
            transformOrigin: '0 0',
            fontVariantLigatures: 'none',
            whiteSpace: 'pre',
          }}
        >
          {grid.lines.map((line, row) => (
            <div key={row} style={{height: cellHeight, display: 'flex'}}>
              {line.map((cell, col) => (
                <span
                  key={col}
                  style={{
                    width: cellWidth,
                    color: cell.fg,
                    backgroundColor: cell.bg,
                    fontWeight: cell.bold ? 700 : 400,
                    fontStyle: cell.italic ? 'italic' : 'normal',
                    textDecoration: cell.underline ? 'underline' : undefined,
                  }}
                >
                  {cell.char}
                </span>
              ))}
            </div>
          ))}
        </div>
      </div>

      {vignette && (
        <AbsoluteFill
          style={{
            pointerEvents: 'none',
            background:
              'radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.55) 100%)',
          }}
        />
      )}

      {debug && (
        <div
          style={{
            position: 'absolute',
            top: 16,
            right: 16,
            padding: '12px 18px',
            fontFamily: '"JetBrains Mono",monospace',
            fontSize: 14,
            color: '#fab387',
            backgroundColor: 'rgba(17,17,27,0.9)',
            border: '1px solid #fab387',
            borderRadius: 6,
            zIndex: 100,
            maxWidth: 1200,
            whiteSpace: 'pre',
          }}
        >
          {`url=${castUrl}\nlines=${grid.lines.length} · non-space=${totalChars} · t=${t.toFixed(2)}s\n`}
          {`events=${grid.eventsApplied ?? '?'}/${grid.totalEvents ?? '?'}\n`}
          {grid.error ? `ERROR: ${grid.error}\n` : ''}
          {sampleLines.map((l, i) => `[${i}] "${l}"\n`).join('')}
        </div>
      )}
    </AbsoluteFill>
  );
};
