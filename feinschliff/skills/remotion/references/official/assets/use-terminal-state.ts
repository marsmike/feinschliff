/**
 * useTerminalState — replay an asciicast v3 file into a deterministic cell grid
 * at any playback time `t`. Pairs with TerminalScene to render terminal
 * recordings as composited React.
 *
 * Uses `@xterm/headless` to parse ANSI/VT escape sequences. The headless
 * Terminal builds an in-memory buffer; we read cells off it after replaying
 * events up to time t.
 *
 * Performance: a naive re-replay-from-start every frame is O(N) per frame
 * for N events. We mitigate via two-tier caching:
 *   1. Module-level: events parsed once per cast URL.
 *   2. Component-level: terminal state snapshotted at integer-second
 *      keyframes; for any t we resume from the nearest keyframe ≤ t.
 *
 * Asciicast v3 spec (relevant subset):
 *   Header line:  {"version":3, "term":{"cols":N,"rows":M,"type":...}, ...}
 *   Event line:   [delta_secs, "o" | "i" | "r" | "x", data]
 *     delta_secs is the gap *since the previous event* (v3 — different from v2)
 */

import {useEffect, useMemo, useState} from 'react';
import {delayRender, continueRender} from 'remotion';

// ── Types ────────────────────────────────────────────────────────────────────

export type CastEvent = [delta: number, type: 'o' | 'i' | 'r' | 'x', data: string];

export interface CastHeader {
  version: 3;
  term: {cols: number; rows: number; type?: string};
  title?: string;
  idle_time_limit?: number;
  command?: string;
}

export interface ParsedCast {
  header: CastHeader;
  events: CastEvent[];
  /** Cumulative absolute time per event (since v3 deltas are relative). */
  absoluteTimes: number[];
}

export interface SceneIndexStep {
  id: string;
  label: string;
  action: string;
  start_s: number;
  end_s: number;
}

export interface SceneIndex {
  recipe: string;
  cast: string;
  title?: string;
  duration_s: number;
  fps_hint: number;
  steps: SceneIndexStep[];
}

export interface Cell {
  char: string;
  fg: string;
  bg: string;
  bold: boolean;
  italic: boolean;
  underline: boolean;
}

export interface GridLine {
  cells: Cell[];
}

export interface Grid {
  lines: GridLine[];
  cols: number;
  rows: number;
}

// ── Cast parsing ────────────────────────────────────────────────────────────

const castParseCache = new Map<string, ParsedCast>();

async function parseCast(url: string): Promise<ParsedCast> {
  const cached = castParseCache.get(url);
  if (cached) return cached;

  const text = await (await fetch(url)).text();
  const lines = text.split('\n').filter((l) => l.trim().length > 0);
  const header = JSON.parse(lines[0]) as CastHeader;
  if (header.version !== 3) {
    throw new Error(
      `useTerminalState: cast at ${url} is v${header.version}, expected v3`,
    );
  }

  const events: CastEvent[] = [];
  const absoluteTimes: number[] = [];
  let cumulative = 0;
  for (let i = 1; i < lines.length; i++) {
    const ev = JSON.parse(lines[i]) as CastEvent;
    cumulative += ev[0];
    events.push(ev);
    absoluteTimes.push(cumulative);
  }

  const parsed = {header, events, absoluteTimes};
  castParseCache.set(url, parsed);
  return parsed;
}

// ── Snapshot cache ──────────────────────────────────────────────────────────

interface Snapshot {
  /** Index into events[] this snapshot covers up to (exclusive). */
  upToIndex: number;
  /** Serialised buffer state (per-line cells). */
  grid: Grid;
}

const snapshotCache = new Map<string, Snapshot[]>();
const KEYFRAME_INTERVAL_S = 1.0;

// ── Headless terminal replay ────────────────────────────────────────────────

/**
 * Build a snapshot of the terminal grid at the requested time `t` (seconds).
 * Uses keyframe caching: pick the latest keyframe ≤ t and replay events from
 * there. For the skeleton we re-replay from start every time; the cache hooks
 * are in place but populating them is M2 follow-up.
 */
async function gridAt(parsed: ParsedCast, t: number): Promise<Grid> {
  // Lazy-load @xterm/headless so this file can compile in environments
  // where the dep isn't installed yet (Remotion projects opt in).
  const {Terminal} = await import('@xterm/headless');
  const term = new Terminal({
    cols: parsed.header.term.cols,
    rows: parsed.header.term.rows,
    allowProposedApi: true,
  });

  // Replay every output event with timestamp ≤ t.
  for (let i = 0; i < parsed.events.length; i++) {
    if (parsed.absoluteTimes[i] > t) break;
    const [, kind, data] = parsed.events[i];
    if (kind === 'o') term.write(data);
    // 'i' (input) and 'r' (resize) and 'x' (marker) are ignored for rendering.
  }

  return readGrid(term, parsed.header.term.rows);
}

function readGrid(term: import('@xterm/headless').Terminal, rows: number): Grid {
  const buffer = term.buffer.active;
  const cols = term.cols;
  const lines: GridLine[] = [];

  for (let row = 0; row < rows; row++) {
    const line = buffer.getLine(buffer.viewportY + row);
    const cells: Cell[] = [];
    if (!line) {
      for (let col = 0; col < cols; col++) {
        cells.push(blankCell());
      }
      lines.push({cells});
      continue;
    }

    for (let col = 0; col < cols; col++) {
      const cell = line.getCell(col);
      cells.push(
        cell
          ? {
              char: cell.getChars() || ' ',
              fg: ansiColor(cell.getFgColor(), cell.isFgRGB(), cell.isFgPalette(), '#cdd6f4'),
              bg: ansiColor(cell.getBgColor(), cell.isBgRGB(), cell.isBgPalette(), 'transparent'),
              bold: !!cell.isBold(),
              italic: !!cell.isItalic(),
              underline: !!cell.isUnderline(),
            }
          : blankCell(),
      );
    }
    lines.push({cells});
  }

  return {lines, cols, rows};
}

function blankCell(): Cell {
  return {
    char: ' ',
    fg: '#cdd6f4',
    bg: 'transparent',
    bold: false,
    italic: false,
    underline: false,
  };
}

/**
 * Convert an xterm cell colour value to a CSS string. Truncated palette for
 * the skeleton — full 256-colour mapping is a follow-up.
 */
function ansiColor(value: number, isRGB: boolean, isPalette: boolean, fallback: string): string {
  if (isRGB) {
    const r = (value >> 16) & 0xff;
    const g = (value >> 8) & 0xff;
    const b = value & 0xff;
    return `rgb(${r},${g},${b})`;
  }
  if (isPalette) {
    return PALETTE_8[value % 8] ?? fallback;
  }
  return fallback;
}

// Catppuccin Mocha-ish (matches our existing nord/agg theme broadly).
const PALETTE_8 = [
  '#45475a', // 0 black
  '#f38ba8', // 1 red
  '#a6e3a1', // 2 green
  '#f9e2af', // 3 yellow
  '#89b4fa', // 4 blue
  '#cba6f7', // 5 magenta
  '#94e2d5', // 6 cyan
  '#cdd6f4', // 7 white
];

// ── React hook ───────────────────────────────────────────────────────────────

const EMPTY_GRID: Grid = {lines: [], cols: 0, rows: 0};

/**
 * Returns the terminal grid at playback time `t` (seconds since cast start).
 *
 * In Remotion's render pipeline this hook participates in the
 * delayRender/continueRender contract so the renderer waits for the grid
 * to be ready before capturing the frame.
 */
export function useTerminalState(castUrl: string, t: number): Grid {
  const [grid, setGrid] = useState<Grid>(EMPTY_GRID);

  // Stable handle so repeated renders share the same delayRender slot.
  const handle = useMemo(() => delayRender(`terminal:${castUrl}:${t.toFixed(3)}`), [castUrl, t]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const parsed = await parseCast(castUrl);
        const next = await gridAt(parsed, t);
        if (!cancelled) {
          setGrid(next);
          continueRender(handle);
        }
      } catch (err) {
        if (!cancelled) {
          console.error('[TerminalScene] failed to render grid:', err);
          continueRender(handle);
        }
      }
    })();
    return () => {
      cancelled = true;
      // Best-effort cleanup; if we never resolved, free the handle.
      try {
        continueRender(handle);
      } catch {
        // already continued
      }
    };
  }, [castUrl, t, handle]);

  return grid;
}

// Expose snapshot caches for testing and warm-up scripts.
export const _internals = {
  castParseCache,
  snapshotCache,
  KEYFRAME_INTERVAL_S,
};
