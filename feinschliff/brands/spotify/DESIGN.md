---
extends: feinschliff
version: alpha
name: Spotify
description: Spotify — Spotify Green accent on near-black canvas, pill-and-circle geometry, heavy shadows, content-first immersion.
colors:
  accent: "#1ed760"
  accent-hover: "#1db954"  # Spotify legacy green — used for pressed / active states.
  highlight: "#509bf5"  # Announcement blue — info states (per Spotify DESIGN.md).
  black: "#ffffff"
  ink: "#000000"
  graphite: "#fdfdfd"  # Body strong on dark — near-pure white for max emphasis.
  steel: "#b3b3b3"
  silver: "#7c7c7c"  # Light border — outlined-pill border, muted links.
  fog: "#4d4d4d"  # Border gray — button borders on dark surfaces.
  paper: "#181818"  # Surface (Level 1) — dark card, sidebar, container surface.
  paper-2: "#252525"  # Dark Card (elevated) — highlighted card surface.
  off-white: "#ffffff"
  off-white-2: "#b3b3b3"  # On-dark soft — secondary labels, footer body.
  rule-dark: "#282828"  # Hairlines on dark surfaces.
  surface-dark: "#121212"
  surface-dark-elevated: "#1f1f1f"  # Mid Dark — pill button background, interactive surfaces.
  surface-dark-soft: "#181818"  # Soft dark band — Surface Level 1 alias.
  surface-soft: "#181818"  # Section dividers, soft band backgrounds.
  surface-cream-strong: "#272727"  # Mid Card — alternate elevated card surface.
  accent-teal: "#509bf5"  # Announcement blue — playlist blue, info indicators.
  success: "#1ed760"  # Status success — Spotify Green.
  warning: "#ffa42b"  # Status warning — Spotify warning orange.
  error: "#f3727f"  # Status error — Spotify negative red.
  white: "#121212"
---

## Overview

Spotify — Spotify Green accent on near-black canvas, pill-and-circle geometry, heavy shadows, content-first immersion. Derived from the public Spotify product surface (getdesign.md/spotify). Not an official Spotify design system. MIT.

## Colors

- `accent` (`#1ed760`) — Spotify Green — the canonical brand accent. Reserved for play controls, active states, primary CTAs. Never decorative.
- `black` (`#ffffff`) — Body ink — on Spotify's dark canvas the default text reads pure-white. Semantic-name kept, value flipped to invert the palette without rewriting layouts.
- `ink` (`#000000`) — Pure black — chapter dividers, deepest contrast band beneath the canvas.
- `steel` (`#b3b3b3`) — Silver — secondary text, muted labels, inactive nav (Spotify DESIGN.md).
- `off-white` (`#ffffff`) — On-dark text — pure white. Also reads on Spotify Green pills.
- `surface-dark` (`#121212`) — Base (Level 0) — Spotify's near-black canvas, the brand-defining backdrop.
- `white` (`#121212`) — Canvas — Spotify's true-black surface. Semantic-name kept, value flipped to invert the palette without rewriting layouts.

## Typography

Defined in tokens.json (`font-family`, `font-weight`, `font-size`).
Inherits from this brand's tokens for now; future revisions may move
typography tokens into DESIGN.md frontmatter.
