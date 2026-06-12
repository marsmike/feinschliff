// Default theme fonts — loaded for their side effects at bundle import time.
// The theme contract defaults to Archivo (titles, weights 700/900) and Inter
// (body, weight 500); without these loads every template silently falls back
// to the renderer's default serif. Brand packs that override fontTitle /
// fontBody still degrade to the generic `sans-serif` suffix the templates
// append.
import {loadFont as loadArchivo} from '@remotion/google-fonts/Archivo';
import {loadFont as loadInter} from '@remotion/google-fonts/Inter';

const archivo = loadArchivo('normal', {weights: ['700', '900']});
const inter = loadInter('normal', {weights: ['500']});

// Resolves when both Google Fonts are fully loaded and available to
// measureText. Templates gate their measuring on this promise via
// useFontsReady() to avoid caching fallback-font metrics in a chunked render.
export const fontsReady: Promise<unknown> = Promise.all([
  archivo.waitUntilDone(),
  inter.waitUntilDone(),
]);
