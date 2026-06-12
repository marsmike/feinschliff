// Shared template helpers — keep this file dependency-free (no React,
// no remotion) so any template can import it without cycles.

export const CLAMP = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

// Heavy multi-layer shadow so cardless type stays legible over the speaker.
export const SHADOW = '0 4px 24px rgba(0,0,0,0.65), 0 1px 4px rgba(0,0,0,0.8)';

// Theme colors are hex strings like #1E2430. Append a two-digit hex alpha
// byte ONLY when the value really is a 7-char #RRGGBB — anything else
// (rgb(...), named colors) passes through unchanged so we never emit an
// invalid color; the fallback degradation is "fully opaque", which still
// reads fine behind the backdrop blur.
export const withAlpha = (color: string, alphaHex: string): string =>
  /^#[0-9a-fA-F]{6}$/.test(color) ? `${color}${alphaHex}` : color;
