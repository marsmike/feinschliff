import React from 'react';
import {Composition} from 'remotion';
import {EditedVideo} from './EditedVideo';
import {StyleShowcase} from './StyleShowcase';
import {DEFAULT_THEME, EditedVideoProps} from './theme';

const FALLBACK: EditedVideoProps = {
  source: '',
  durationSec: 10,
  width: 1080,
  height: 1920,
  fps: 30,
  beats: [],
  zoom: [],
  theme: DEFAULT_THEME,
};

export const Root: React.FC = () => (
  <>
    <Composition
      id="EditedVideo"
      component={EditedVideo}
      durationInFrames={300}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={FALLBACK}
      calculateMetadata={async ({props}) => ({
        durationInFrames: Math.max(1, Math.ceil(props.durationSec * props.fps)),
        fps: props.fps,
        width: props.width,
        height: props.height,
        props,
      })}
    />
    <Composition
      id="StyleShowcase"
      component={StyleShowcase}
      durationInFrames={270}
      fps={30}
      width={1080}
      height={1920}
    />
  </>
);
