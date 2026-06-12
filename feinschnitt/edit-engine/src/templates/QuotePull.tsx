import React, {useMemo} from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {measureText} from '@remotion/layout-utils';
import {Beat, Theme} from '../theme';
import {useFontsReady} from '../use-fonts-ready';

const CLAMP = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// quote_pull — full takeover typewriter quote.
export const QuotePull: React.FC<{beat: Beat; theme: Theme}> = ({beat, theme}) => {
  const frame = useCurrentFrame(); // relative to this beat's Sequence
  const {width, fps} = useVideoConfig();
  const fontsLoaded = useFontsReady();

  // Plans come from an LLM — coerce instead of trusting the string type.
  const quoteText = String(beat.quote_text ?? '');
  const attribution = String(beat.attribution ?? '');
  // chars_per_second is stamped by the Python alignment stage; fall back to a
  // readable default when absent (Studio / hand-written plans).
  const cpsRaw = Number(beat.chars_per_second);
  const cps = Number.isFinite(cpsRaw) && cpsRaw > 0 ? cpsRaw : 14;

  // Generic fallback keeps arbitrary brand stacks degrading to sans, never serif.
  const titleFamily = `${theme.fontTitle}, sans-serif`;
  const bodyFamily = `${theme.fontBody}, sans-serif`;

  // Typing starts after a 0.30s container fade-in — matches Python QUOTE_GLYPH_LEAD=0.30
  // at any fps (not a literal 9-frame constant tied to 30 fps).
  const entranceFrames = Math.round(0.3 * fps);

  // Unicode-safe character split: JS .length counts UTF-16 units, but the
  // Python side counted code points with len() when stamping cps — Array.from
  // matches Python and never splits surrogate pairs.
  const chars = Array.from(quoteText);
  const totalChars = chars.length;

  // Auto-fit: MEASURE the longest authored line and scale so it fits ~86% of
  // frame width — never overflow (invariant). measureText must see the exact
  // fontFamily string the element renders with. Guard behind fontsLoaded so we
  // never cache a fallback-font measurement (would cause inter-chunk size jumps).
  const lines = quoteText.split('\n');
  const base = width * 0.075;
  const fontSize = useMemo(() => {
    if (!fontsLoaded) return base; // delayRender holds the frame; this is never captured
    const maxLineWidth = Math.max(
      1,
      ...lines.map(
        (line) =>
          measureText({text: line, fontFamily: titleFamily, fontWeight: '700', fontSize: base})
            .width,
      ),
    );
    return base * Math.min(1, (width * 0.86) / maxLineWidth);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fontsLoaded, quoteText, titleFamily, base, width]);

  // Typewriter clock: characters appear at `cps` once the entrance settles.
  const visibleChars = Math.min(
    totalChars,
    Math.max(0, Math.floor(((frame - entranceFrames) / fps) * cps)),
  );
  const typingDone = visibleChars >= totalChars;
  // First frame at which visibleChars reaches totalChars (same formula, inverted).
  const typingDoneFrame = entranceFrames + Math.ceil((totalChars * fps) / cps);

  const containerOpacity = interpolate(frame, [0, entranceFrames], [0, 1], CLAMP);
  const attributionOpacity = interpolate(
    frame,
    [typingDoneFrame + 10, typingDoneFrame + 20],
    [0, 1],
    CLAMP,
  );

  // No reflow while typing: the FULL text is laid out from frame 0 — every
  // character renders in a <span> that flips opacity 0→1, and each authored
  // line is its own whiteSpace:'pre' <div>, so line breaks CANNOT shift as
  // characters appear (no wrapping, newlines are real block breaks).
  // Character indices are GLOBAL across the whole text (newlines included),
  // matching the Python code-point count.
  let globalIndex = 0;
  const renderedLines = lines.map((line, lineIdx) => {
    const lineChars = Array.from(line);
    const lineStart = globalIndex;
    // The caret sits after the last visible character of this line: it stays
    // at the end of a finished line until the '\n' itself "types", then jumps
    // to the start of the next line.
    const caretHere =
      !typingDone && visibleChars >= lineStart && visibleChars <= lineStart + lineChars.length;
    const caretLocal = visibleChars - lineStart;
    globalIndex += lineChars.length + 1; // +1 for the consumed '\n'
    return (
      <div key={lineIdx} style={{whiteSpace: 'pre', minHeight: '1.35em'}}>
        {lineChars.map((ch, i) => (
          <React.Fragment key={i}>
            {/* Inserting the caret BEFORE the next (invisible) character only
                shifts invisible spans — visible glyphs never move. */}
            {caretHere && i === caretLocal ? <Caret theme={theme} /> : null}
            <span style={{opacity: lineStart + i < visibleChars ? 1 : 0}}>{ch}</span>
          </React.Fragment>
        ))}
        {caretHere && caretLocal >= lineChars.length ? <Caret theme={theme} /> : null}
      </div>
    );
  });

  return (
    // Takeover backdrop is STATIC — full opacity from frame 0; only the
    // foreground animates. Prevents the speaker flickering through during
    // entrance frames (invariant 3).
    <AbsoluteFill
      style={{
        backgroundColor: theme.bg,
        justifyContent: 'center',
        alignItems: 'center',
        flexDirection: 'column',
      }}
    >
      <div
        style={{
          maxWidth: '86%',
          color: theme.text,
          fontFamily: titleFamily,
          fontWeight: 700,
          fontSize,
          lineHeight: 1.35,
          textAlign: 'left',
          opacity: containerOpacity,
        }}
      >
        {renderedLines}
        {attribution ? (
          <div
            style={{
              color: theme.muted,
              fontFamily: bodyFamily,
              fontWeight: 500,
              fontSize: width * 0.03,
              marginTop: '0.9em',
              opacity: attributionOpacity,
            }}
          >
            {`— ${attribution}`}
          </div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

// The caret is the ONE accent element in this takeover (accent monogamy).
const Caret: React.FC<{theme: Theme}> = ({theme}) => (
  <span
    style={{
      display: 'inline-block',
      width: '0.08em',
      height: '0.6em',
      marginLeft: '0.08em',
      backgroundColor: theme.accent,
    }}
  />
);
