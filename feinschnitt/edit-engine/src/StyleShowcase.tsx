import React from 'react';
import {AbsoluteFill, Sequence, useVideoConfig} from 'remotion';
import {Beat, DEFAULT_THEME} from './theme';
import {HookTitle} from './templates/HookTitle';
import {StatPunch} from './templates/StatPunch';
import {WordPop} from './templates/WordPop';

// StyleShowcase — the golden comp. One Sequence per template kind against a
// mid-gray background (#444) so legibility shadows are visible.
// Extend with every new template kind — this comp is the visual contract for
// the whole library.

const HOOK: Beat = {
  kind: 'hook_title',
  start_sec: 0,
  end_sec: 3,
  kicker: 'TWO PEOPLE · WITH AI',
  title: '$400M',
  vertical: 0.6,
};

const WORD_POP: Beat = {
  kind: 'word_pop',
  start_sec: 3,
  end_sec: 6,
  items: [
    {text: 'ChatGPT', appear_sec: 3.0},
    {text: '{Claude}', appear_sec: 4.0},
    {text: 'Grok', appear_sec: 5.0, accent: true},
  ],
};

const STAT: Beat = {
  kind: 'stat_punch',
  start_sec: 6,
  end_sec: 9,
  value: '10×',
  caption: 'faster than hand-editing',
};

export const StyleShowcase: React.FC = () => {
  const {fps} = useVideoConfig();
  // Same Sequence boundary rounding as EditedVideo.tsx — items inside beats
  // resolve their offsets against these exact frame numbers (invariant 2).
  const seg = (beat: Beat) => ({
    from: Math.round(beat.start_sec * fps),
    durationInFrames: Math.max(
      1,
      Math.round(beat.end_sec * fps) - Math.round(beat.start_sec * fps),
    ),
  });
  return (
    <AbsoluteFill style={{backgroundColor: '#444'}}>
      <Sequence {...seg(HOOK)}>
        <HookTitle beat={HOOK} theme={DEFAULT_THEME} />
      </Sequence>
      <Sequence {...seg(WORD_POP)}>
        <WordPop beat={WORD_POP} theme={DEFAULT_THEME} />
      </Sequence>
      <Sequence {...seg(STAT)}>
        <StatPunch beat={STAT} theme={DEFAULT_THEME} />
      </Sequence>
    </AbsoluteFill>
  );
};
