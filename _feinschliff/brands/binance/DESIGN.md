---
extends: feinschliff
version: alpha
name: Binance
description: Binance — bold Binance Yellow accent on a deep crypto-black canvas, trading-floor urgency, BinanceNova / BinancePlex stack (IBM Plex substitute), tabular numerics.
colors:
  accent: "#fcd535"
  accent-active: "#f0b90b"
  accent-disabled: "#3a3a1f"
  accent-hover: "#f0b90b"
  highlight: "#fcd535"
  black: "#eaecef"
  ink: "#0b0e11"
  graphite: "#ffffff"
  steel: "#b7bdc6"  # Body emphasized on dark — lead text, secondary display.
  silver: "#848e9c"
  fog: "#2b3139"
  fog-strong: "#eaecef"
  paper: "#1e2329"
  paper-2: "#2b3139"
  paper-3: "#181a20"  # Code-block / terminal background inside dark cards.
  off-white: "#eaecef"  # On-dark text — soft cool white that echoes the body ink.
  off-white-2: "#848e9c"  # On-dark soft — footer body text, secondary labels.
  rule-dark: "#2b3139"  # Hairlines on dark surfaces (alias of fog).
  surface-dark: "#0b0e11"
  surface-dark-elevated: "#1e2329"
  surface-dark-soft: "#181a20"
  surface-soft: "#181a20"
  surface-cream-strong: "#2b3139"  # Strongest surface — selected tabs, emphasized bands.
  canvas-light: "#ffffff"
  surface-soft-light: "#fafafa"
  surface-strong-light: "#f5f5f5"  # Light-band stronger surface — disabled, dividers.
  ink-on-light: "#181a20"
  trading-up: "#0ecb81"
  trading-down: "#f6465d"
  accent-teal: "#3b82f6"
  success: "#0ecb81"  # Status success — alias of trading-up.
  warning: "#fcd535"  # Status warning — Binance Yellow doubles as caution.
  error: "#f6465d"  # Status error — alias of trading-down.
  white: "#0b0e11"
---

## Overview

Binance — bold Binance Yellow accent on a deep crypto-black canvas, trading-floor urgency, BinanceNova / BinancePlex stack (IBM Plex substitute), tabular numerics. Single accent does all brand voltage; trading-up green / trading-down red are semantic price-direction tokens, never decorative. Multi-theme: dark for marketing/product, light for transactional surfaces — the deck reuses the light palette ONLY for the closing footer-reset band that closes every Binance page. Flat surfaces, no shadows. Derived from getdesign.md/binance/design-md. MIT.

## Colors

- `accent` (`#fcd535`) — Binance Yellow — the single brand-defining accent. Reserved for primary CTAs, the wordmark, hero / brand-claim headlines, trust-badge numerics. Used scarcely on dark for emphasis. Never decorative. NEVER as body fill.
- `accent-active` (`#f0b90b`) — Binance Yellow active / pressed — slightly more saturated yellow.
- `accent-disabled` (`#3a3a1f`) — Binance Yellow disabled — desaturated dark-yellow on dark canvas.
- `accent-hover` (`#f0b90b`) — Alias of accent-active. Per the no-hover policy this is not used in preview output, but kept for theme.xml compatibility.
- `highlight` (`#fcd535`) — Companion bright yellow — small inline highlights, badges, focus rings. Same hex as accent — Binance has one yellow.
- `black` (`#eaecef`) — Body ink — on Binance's dark canvas the default text reads as soft cool white. Semantic-name kept; value flipped to invert the palette without rewriting layouts.
- `ink` (`#0b0e11`) — Pure crypto-black — chapter dividers, deepest contrast band beneath the canvas.
- `graphite` (`#ffffff`) — Body strong on dark — pure white for max emphasis on display copy.
- `silver` (`#848e9c`) — Muted on dark — sub-headings, breadcrumbs, secondary labels (DESIGN.md `muted`).
- `fog` (`#2b3139`) — Hairline border on dark surfaces — separator strokes, ticker-row dividers (DESIGN.md `hairline-on-dark`). Same hex as surface-card-dark elevated; reads as a brightness-step.
- `fog-strong` (`#eaecef`) — 1px hairline on light footer-reset bands (DESIGN.md `hairline-on-light`). Highest-frequency token on the brand surface.
- `paper` (`#1e2329`) — Elevated card surface — feature cards, content cards, the markets-table-card and trust-badges (DESIGN.md `surface-card-dark`).
- `paper-2` (`#2b3139`) — Strongest elevated surface — emphasized cards, nested cards, hover (DESIGN.md `surface-elevated-dark`). Same hex as fog; the elevation IS the hairline tone.
- `surface-dark` (`#0b0e11`) — Trading-pane / cover surface — Binance deep crypto-black. Slightly warm tinted, never pure black.
- `surface-dark-elevated` (`#1e2329`) — Elevated cards inside dark bands — markets-table-card, ticker tile, trust badges.
- `surface-dark-soft` (`#181a20`) — Code block / terminal backgrounds inside dark cards. Slightly lifted from canvas.
- `surface-soft` (`#181a20`) — Section dividers, soft band backgrounds — never light, Binance is dark-first.
- `canvas-light` (`#ffffff`) — Light footer-reset canvas — used ONLY in the closing-page light band that visually closes every Binance page (DESIGN.md `canvas-light`). Never on body slides.
- `surface-soft-light` (`#fafafa`) — Light footer band surface — the iconic 'marketing reset' that closes every page (DESIGN.md `surface-soft-light`).
- `ink-on-light` (`#181a20`) — Default text on the light footer-reset band (DESIGN.md `ink` / `body-on-light`).
- `trading-up` (`#0ecb81`) — Price-up green — semantic price-direction signal. Used as text colour in tables, charts, inline ticker arrows. NEVER as a button background; NEVER for generic 'success'.
- `trading-down` (`#f6465d`) — Price-down red — semantic price-direction signal. Same usage rules as trading-up; NEVER as a generic 'error'.
- `accent-teal` (`#3b82f6`) — Info / focus-ring blue (DESIGN.md `info`). Single-product accent (Smart Money) — treat as a system info colour, not a brand colour.
- `white` (`#0b0e11`) — Canvas — Binance deep crypto-black, the brand-defining dark backdrop. Semantic-name kept; value flipped to invert the palette without rewriting layouts.

## Typography

Defined in tokens.json (`font-family`, `font-weight`, `font-size`).
Inherits from this brand's tokens for now; future revisions may move
typography tokens into DESIGN.md frontmatter.
