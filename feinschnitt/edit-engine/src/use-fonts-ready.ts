import {useEffect, useState} from 'react';
import {continueRender, delayRender} from 'remotion';
import {fontsReady} from './fonts';

// Gate measureText behind font readiness: measuring with the fallback font
// poisons layout-utils' cache for the whole render tab (inter-chunk size
// jumps). delayRender holds the screenshot until the re-render with loaded
// fonts has happened, so captured frames always use real metrics.
export const useFontsReady = (): boolean => {
  const [ready, setReady] = useState(false);
  const [handle] = useState(() => delayRender('webfonts for measureText'));
  useEffect(() => {
    let active = true;
    fontsReady.then(() => {
      if (active) {
        setReady(true);
      }
      continueRender(handle);
    });
    return () => {
      active = false;
    };
  }, [handle]);
  return ready;
};
