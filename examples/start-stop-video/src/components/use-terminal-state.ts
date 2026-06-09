/**
 * useTerminalState — replay an asciicast v3 file into a deterministic cell grid
 * at any playback time `t`. Demo implementation — concrete and working, less
 * elegant than the reference at feinschliff/skills/remotion/references/.
 */

import {useEffect, useMemo, useState} from 'react';
import {delayRender, continueRender} from 'remotion';

export type CastEvent = [delta: number, type: 'o' | 'i' | 'r' | 'x', data: string];

export interface ParsedCast {
  cols: number;
  rows: number;
  events: CastEvent[];
  absoluteTimes: number[];
}

export interface Cell {
  char: string;
  fg: string;
  bg: string;
  bold: boolean;
  italic: boolean;
  underline: boolean;
}

export interface Grid {
  lines: Cell[][];
  cols: number;
  rows: number;
  /** Diagnostic: how many events were applied to produce this grid. */
  eventsApplied?: number;
  /** Diagnostic: how many total events were in the cast. */
  totalEvents?: number;
  /** Diagnostic: error message, if any. */
  error?: string;
}

const castCache = new Map<string, Promise<ParsedCast>>();

async function parseCast(url: string): Promise<ParsedCast> {
  if (castCache.has(url)) return castCache.get(url)!;
  const promise = (async () => {
    const res = await fetch(url);
    const text = await res.text();
    const lines = text.split('\n').filter((l) => l.trim().length > 0);
    const header = JSON.parse(lines[0]);
    const events: CastEvent[] = [];
    const absoluteTimes: number[] = [];
    let cum = 0;
    for (let i = 1; i < lines.length; i++) {
      const ev = JSON.parse(lines[i]) as CastEvent;
      cum += ev[0];
      events.push(ev);
      absoluteTimes.push(cum);
    }
    return {cols: header.term.cols, rows: header.term.rows, events, absoluteTimes};
  })();
  castCache.set(url, promise);
  return promise;
}

const PALETTE_16 = [
  '#45475a', '#f38ba8', '#a6e3a1', '#f9e2af',
  '#89b4fa', '#cba6f7', '#94e2d5', '#cdd6f4',
  '#585b70', '#f37799', '#a6d189', '#e5c890',
  '#7fa3e8', '#b0a0e8', '#81c8be', '#bac2de',
];

function colorOf(value: number, isRGB: boolean, isPalette: boolean, fallback: string): string {
  if (isRGB) {
    const r = (value >> 16) & 0xff;
    const g = (value >> 8) & 0xff;
    const b = value & 0xff;
    return `rgb(${r},${g},${b})`;
  }
  if (isPalette) {
    if (value < 16) return PALETTE_16[value];
    if (value < 232) {
      // 6×6×6 cube
      const i = value - 16;
      const r = Math.floor(i / 36) * 51;
      const g = Math.floor((i % 36) / 6) * 51;
      const b = (i % 6) * 51;
      return `rgb(${r},${g},${b})`;
    }
    // Greyscale 232..255
    const v = (value - 232) * 10 + 8;
    return `rgb(${v},${v},${v})`;
  }
  return fallback;
}

async function gridAt(parsed: ParsedCast, t: number): Promise<Grid> {
  const {Terminal} = await import('@xterm/headless');
  const term = new Terminal({
    cols: parsed.cols,
    rows: parsed.rows,
    allowProposedApi: true,
    scrollback: 1000,
  });
  let applied = 0;
  for (let i = 0; i < parsed.events.length; i++) {
    if (parsed.absoluteTimes[i] > t) break;
    const [, kind, data] = parsed.events[i];
    if (kind === 'o') {
      term.write(data);
      applied++;
    }
  }
  // term.write() queues data; xterm's parser processes asynchronously.
  // The callback signature lets us await the queue draining cleanly.
  await new Promise<void>((resolve) => term.write('', resolve));
  const g = readGrid(term, parsed.rows);
  g.eventsApplied = applied;
  g.totalEvents = parsed.events.length;
  return g;
}

function readGrid(term: import('@xterm/headless').Terminal, rows: number): Grid {
  const buf = term.buffer.active;
  const cols = term.cols;
  const lines: Cell[][] = [];
  // The visible viewport is the last `rows` lines of the buffer (after any
  // scrolling). buf.length includes scrollback; the viewport is from
  // (buf.length - rows) to (buf.length - 1).
  const viewportStart = Math.max(0, buf.length - rows);
  for (let row = 0; row < rows; row++) {
    const line = buf.getLine(viewportStart + row);
    const cells: Cell[] = [];
    for (let col = 0; col < cols; col++) {
      const cell = line?.getCell(col);
      if (!cell) {
        cells.push({char: ' ', fg: '#cdd6f4', bg: 'transparent', bold: false, italic: false, underline: false});
        continue;
      }
      cells.push({
        char: cell.getChars() || ' ',
        fg: colorOf(cell.getFgColor(), !!cell.isFgRGB(), !!cell.isFgPalette(), '#cdd6f4'),
        bg: colorOf(cell.getBgColor(), !!cell.isBgRGB(), !!cell.isBgPalette(), 'transparent'),
        bold: !!cell.isBold(),
        italic: !!cell.isItalic(),
        underline: !!cell.isUnderline(),
      });
    }
    lines.push(cells);
  }
  return {lines, cols, rows};
}

const EMPTY_GRID: Grid = {lines: [], cols: 0, rows: 0};

export function useTerminalState(castUrl: string, t: number): Grid {
  const [grid, setGrid] = useState<Grid>(EMPTY_GRID);
  const handle = useMemo(
    () => delayRender(`terminal:${castUrl}@${t.toFixed(3)}`),
    [castUrl, t],
  );
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const parsed = await parseCast(castUrl);
        const g = await gridAt(parsed, t);
        if (!cancelled) setGrid(g);
      } catch (err) {
        const msg = err instanceof Error ? `${err.name}: ${err.message}` : String(err);
        if (!cancelled) {
          setGrid({
            lines: [],
            cols: 0,
            rows: 0,
            error: msg,
          });
        }
      } finally {
        if (!cancelled) continueRender(handle);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [castUrl, t, handle]);
  return grid;
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
