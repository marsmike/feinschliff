// Default theme fonts — loaded for their side effects at bundle import time.
// The theme contract defaults to Archivo (titles, weights 700/900) and Inter
// (body, weight 500); without these loads every template silently falls back
// to the renderer's default serif. Brand packs that override fontTitle /
// fontBody still degrade to the generic `sans-serif` suffix the templates
// append.
import {loadFont as loadArchivo} from '@remotion/google-fonts/Archivo';
import {loadFont as loadInter} from '@remotion/google-fonts/Inter';

loadArchivo('normal', {weights: ['700', '900']});
loadInter('normal', {weights: ['500']});
