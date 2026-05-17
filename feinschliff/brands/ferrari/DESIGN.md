---
extends: feinschliff
version: alpha
name: Ferrari
description: Ferrari — Italian motoring heritage as cinematic editorial.
colors:
  accent: "#da291c"
  accent-hover: "#b01e0a"  # Rosso Corsa active / pressed.
  accent-deep: "#9d2211"
  highlight: "#fff200"
  black: "#ffffff"
  ink: "#ffffff"
  graphite: "#ffffff"
  steel: "#969696"  # Default running body text on dark — DESIGN.md `body`.
  silver: "#666666"  # Sub-titles, captions on dark — DESIGN.md `muted`.
  fog: "#303030"
  fog-strong: "#d2d2d2"
  paper: "#181818"
  paper-2: "#303030"
  paper-3: "#212121"  # Section divider band, slightly lifted from canvas.
  paper-4: "#2a2a2a"  # Strongest dark surface — emphasized bands.
  off-white: "#ffffff"  # On-dark text — pure white.
  off-white-2: "#969696"
  rule-dark: "#303030"  # Hairlines on dark surfaces (alias of fog).
  surface-dark: "#181818"
  surface-dark-elevated: "#303030"
  surface-dark-soft: "#212121"  # Soft chapter-section dark band — barely lifted from canvas.
  surface-soft: "#212121"  # Section dividers, soft band backgrounds.
  surface-cream-strong: "#2a2a2a"  # Strongest dark surface — selected tabs, emphasized bands.
  canvas-light: "#ffffff"
  surface-soft-light: "#f7f7f7"  # Light editorial alternating band.
  surface-strong-light: "#ebebeb"  # Light-canvas dividers, badges.
  ink-on-light: "#181818"  # Default text on light editorial bands.
  accent-teal: "#4c98b9"
  success: "#03904a"  # Status success — DESIGN.md `semantic-success`.
  warning: "#f13a2c"
  error: "#da291c"  # Status error — Rosso Corsa.
  white: "#181818"
---

## Overview

Ferrari — Italian motoring heritage as cinematic editorial. Near-black canvas (#181818, never pure black), single sans family (FerrariSans / Inter substitute) at modest weights (display 500, body 400, button 700), Rosso Corsa #DA291C used scarcely — primary CTAs, F1 race-position highlights only. Sharp 0px corners on every CTA, card and band: rectangular precision IS the brand. Cinematic full-bleed photography is the page chrome. Display headlines carry signature negative letter-spacing (-1.6px on display-mega, scaled). Derived from getdesign.md/ferrari (luxury automotive, chiaroscuro editorial). MIT.

## Colors

- `accent` (`#da291c`) — Rosso Corsa — Ferrari's iconic racing red. Reserved for primary CTAs, the Cavallino mark, F1 race-position highlights. Used scarcely — never decorative.
- `accent-deep` (`#9d2211`) — Rosso Corsa darker — documented for completeness; per the no-hover policy this is not used in preview output.
- `highlight` (`#fff200`) — Hypersail yellow — focus-ring + the Hypersail sailing program ONLY. NOT a general accent. Off-brand outside that scope.
- `black` (`#ffffff`) — Body ink on Ferrari's near-black canvas reads pure white. Semantic-name kept, value flipped to invert the palette without rewriting layouts.
- `ink` (`#ffffff`) — Display + body emphasis on dark canvas — pure white per Ferrari DESIGN.md.
- `graphite` (`#ffffff`) — Body strong — same as ink. Ferrari has no second tier on dark.
- `fog` (`#303030`) — 1px hairline divider on dark — DESIGN.md `hairline`. Same hex as canvas-elevated; reads as a brightness-step.
- `fog-strong` (`#d2d2d2`) — 1px hairline on light editorial bands — DESIGN.md `hairline-on-light`.
- `paper` (`#181818`) — Canvas — Ferrari's near-black surface, slightly warm. NEVER pure black. The brand-defining cinema floor.
- `paper-2` (`#303030`) — Canvas elevated — driver cards, livery photo plates (DESIGN.md `canvas-elevated` / `surface-card`).
- `off-white-2` (`#969696`) — On-dark soft — secondary labels, footer body (DESIGN.md `body`).
- `surface-dark` (`#181818`) — Cinematic canvas — the dominant surface. Pure white display type sits on this.
- `surface-dark-elevated` (`#303030`) — Driver / spec / preowned cards on dark canvas (DESIGN.md `canvas-elevated`).
- `canvas-light` (`#ffffff`) — Editorial light band — preowned listings, pricing tables only. Used scarcely.
- `accent-teal` (`#4c98b9`) — Semantic info — info badges, callout backgrounds (DESIGN.md `semantic-info`).
- `warning` (`#f13a2c`) — Status warning / validation error — DESIGN.md `semantic-warning`.
- `white` (`#181818`) — Canvas — Ferrari's near-black surface. Semantic-name kept, value flipped to invert the palette without rewriting layouts.

## Typography

Defined in tokens.json (`font-family`, `font-weight`, `font-size`).
Inherits from this brand's tokens for now; future revisions may move
typography tokens into DESIGN.md frontmatter.
