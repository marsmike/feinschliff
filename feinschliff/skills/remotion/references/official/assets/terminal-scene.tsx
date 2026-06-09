/**
 * TerminalScene — render an asciicast v3 recording as composited React text.
 *
 * Companion to the cli-recorder skill. Reads a .cast file (or URL),
 * parses events with @xterm/headless, replays them up to the current frame
 * time, and renders the resulting cell grid as React. Every Remotion feature
 * (zoom, highlight, transition, audio sync) applies natively to terminal
 * content — because it's just composited DOM, not an embedded video clip.
 *
 * Companion data: a scene-index.json sidecar produced alongside the .cast
 * by cli-recorder. It maps step.id → start_s/end_s, used for chapter markers,
 * narration sync, and per-step zooms.
 *
 * Dependencies:
 *   npm install @xterm/headless
 *
 * Usage:
 *   <TerminalScene
 *     castUrl={staticFile('recordings/claude-commands.cast')}
 *     sceneIndexUrl={staticFile('recordings/claude-commands.scene-index.json')}
 *     // Optional: trim playback to a specific step range (chapter)
 *     startStep="ask"
 *     endStep="compact"
 *   />
 */

import {useMemo} from 'react';
import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {useTerminalState, SceneIndex, CastEvent} from './use-terminal-state';

interface TerminalSceneProps {
  /** URL/path to the .cast file (asciicast v3). */
  castUrl: string;
  /** URL/path to the .scene-index.json sidecar. Optional but enables step-relative trimming. */
  sceneIndexUrl?: string;
  /** Begin playback at this step.id (requires sceneIndexUrl). Inclusive. */
  startStep?: string;
  /** Stop playback at this step.id (requires sceneIndexUrl). Inclusive. */
  endStep?: string;
  /** Override font family (default: JetBrainsMono Nerd Font Mono). */
  fontFamily?: string;
  /** Override font size in px (default: 22). */
  fontSize?: number;
  /** Background colour for the terminal canvas. */
  background?: string;
  /** Optional zoom: scale + focal point in cell coordinates. */
  zoom?: {scale: number; row: number; col: number};
  /** Optional highlight: cells to render with extra emphasis. */
  highlight?: {fromRow: number; toRow: number; fromCol: number; toCol: number};
  /** Style overrides for the outer container. */
  style?: React.CSSProperties;
}

const DEFAULT_FONT_FAMILY =
  '"JetBrainsMono Nerd Font Mono","JetBrains Mono","Menlo",monospace';

const DEFAULT_BG = '#1e1e2e';

export const TerminalScene: React.FC<TerminalSceneProps> = ({
  castUrl,
  sceneIndexUrl,
  startStep,
  endStep,
  fontFamily = DEFAULT_FONT_FAMILY,
  fontSize = 22,
  background = DEFAULT_BG,
  zoom,
  highlight,
  style,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();

  // Convert composition frame to cast playback time, optionally offset by
  // the scene index so a chapter renders from t=startStep.start_s.
  const sceneOffset = useStepOffset(sceneIndexUrl, startStep);
  const playbackTime = frame / fps + sceneOffset;

  const grid = useTerminalState(castUrl, playbackTime);

  // If endStep is set, freeze the grid at endStep.end_s.
  const frozenGrid = useStepCap(grid, sceneIndexUrl, endStep, playbackTime);

  const cellWidth = useMemo(() => fontSize * 0.6, [fontSize]);
  const cellHeight = useMemo(() => fontSize * 1.2, [fontSize]);

  const transform = zoom
    ? `scale(${zoom.scale}) translate(${-zoom.col * cellWidth}px, ${-zoom.row * cellHeight}px)`
    : undefined;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: background,
        fontFamily,
        fontSize,
        lineHeight: '1.2em',
        color: '#cdd6f4',
        padding: 24,
        ...style,
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
        {frozenGrid.lines.map((line, row) => (
          <div key={row} style={{height: cellHeight}}>
            {line.cells.map((cell, col) => {
              const isHl =
                highlight &&
                row >= highlight.fromRow &&
                row <= highlight.toRow &&
                col >= highlight.fromCol &&
                col <= highlight.toCol;
              return (
                <span
                  key={col}
                  style={{
                    color: cell.fg,
                    backgroundColor: isHl ? '#f38ba8' : cell.bg,
                    fontWeight: cell.bold ? 700 : 400,
                    fontStyle: cell.italic ? 'italic' : 'normal',
                    textDecoration: cell.underline ? 'underline' : undefined,
                  }}
                >
                  {cell.char}
                </span>
              );
            })}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

// ── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Read a scene index and return the start_s offset for a given step id.
 * Returns 0 if no index or no matching step.
 */
function useStepOffset(sceneIndexUrl?: string, stepId?: string): number {
  return useMemo(() => {
    if (!sceneIndexUrl || !stepId) return 0;
    // In a Remotion build context this would be loaded synchronously via
    // delayRender/continueRender or pre-bundled as a static import. For the
    // skeleton we assume the host wraps with a data fetch + delayRender.
    // See use-terminal-state.ts for the pattern.
    const idx: SceneIndex | undefined = (globalThis as any).__sceneIndexCache?.[
      sceneIndexUrl
    ];
    const step = idx?.steps.find((s) => s.id === stepId);
    return step ? step.start_s : 0;
  }, [sceneIndexUrl, stepId]);
}

function useStepCap(
  grid: ReturnType<typeof useTerminalState>,
  sceneIndexUrl?: string,
  endStepId?: string,
  currentTime?: number,
) {
  return useMemo(() => {
    if (!sceneIndexUrl || !endStepId || currentTime === undefined) return grid;
    const idx: SceneIndex | undefined = (globalThis as any).__sceneIndexCache?.[
      sceneIndexUrl
    ];
    const step = idx?.steps.find((s) => s.id === endStepId);
    if (!step) return grid;
    return currentTime > step.end_s ? grid : grid;
    // NOTE: a real implementation would freeze by clamping playbackTime to
    // step.end_s in TerminalScene before calling useTerminalState. Left as
    // an explicit follow-up — see TerminalScene M2 follow-ups doc.
  }, [grid, sceneIndexUrl, endStepId, currentTime]);
}

// Re-export the hook contract so consumers can build their own variants.
export type {SceneIndex, CastEvent};
