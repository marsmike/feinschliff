# Changelog

All notable changes to this project will be documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows [SemVer](https://semver.org/).

## [Unreleased]

### Removed
- **`feinblick`** — the codebase-intelligence plugin moved to the `agentic-toolkit` marketplace as `codescan` (an internal static-analysis / audit tool, unrelated to media creation). Its self-audit config (`feinblick.toml` + the `.feinblick/` baseline) is dropped from this repo too.
- **`feinklang-consumer`** — the throwaway Phase-0 cross-plugin smoke-test plugin (already de-listed from the marketplace).

## [0.3.0] - 2026-06-10

- **Repository & marketplace identity: `feinschmiede`.** The umbrella repo/marketplace is now named **feinschmiede** — the same name as the shared engine package — to describe the whole branded-media family over one engine. The office/decks plugin keeps the name `feinschliff`; `feinschliff-builder`/`feinschliff-extra`, the `FEINSCHLIFF_BRAND_PATH`/`~/.feinschliff` overrides, and the `@feinschmiede` install suffixes are unchanged. In-repo links, badges, and install commands now point at `marsmike/feinschmiede` (`/plugin marketplace add marsmike/feinschmiede` → `/plugin install <name>@feinschmiede`). The GitHub repo + Pages rename is the final manual flip; old `marsmike/feinschliff` URLs auto-redirect afterward.
- **feinblick (codebase-intelligence plugin).** New standalone, stdlib-only plugin: unified Python + Claude-skill findings, an audit gate, and an agent-consumable report via the `feinblick` CLI.
- **feinschnitt (video plugin).** Extracted the `remotion` + `cli-recorder` skills out of `feinschliff` into a new full-family `feinschnitt` plugin (bin/ launcher + `feinschnitt record`/`analyze` CLI over a bundled-wheel venv). Voiceover now calls the bare `feinklang tts` CLI; storyboard images call `feinbild imagine`. `plugin.json dependencies: [feinbild, feinklang]`. Recordings land in `${CLAUDE_PROJECT_DIR}/.recordings/`.
- **Audio consolidated into feinklang.** Retired `feinschliff`'s legacy ElevenLabs `/tts` skill (`skills/elevenlabs` + `commands/tts.md`) — its `tts.sh`/`voices.sh` shell scripts and JSON-param docs are fully superseded by the canonical `feinklang` CLI (`feinklang tts` / `feinklang voices`). Audio is now exclusively feinklang's domain.
- **Suite-wide design review hardening.** Engine: SVG validation no longer needs lxml (stdlib ElementTree), token loading unified through one loader, accurate libcairo-vs-Playwright render errors. Distribution: every plugin's `bin/` launcher + `build-wheels.sh` are generated from one manifest (`scripts/gen_launchers.py`) with a fixed update-detection content signature, atomic wheelhouse assembly, and lock-pinned (`constraints.txt`) installs; feinklang/feinschnitt/feinblick joined the uv workspace; all Python packages aligned to one version. Office↔builder: advanced `deck` subcommands delegate to the `feinschliff-builder` CLI instead of a cross-venv import. CI now covers every package, the production render path, and the wheel-install path; skill docs use the bare-CLI contract. Marketplace de-lists the Phase-0 `feinklang-consumer` smoke test.

## [0.2.0] - 2026-05-21

### Added
- **Deck-wide layout budget planning** (`feinschliff/lib/layout_budget.py`) — `feinschliff deck plan-skeleton` now runs a second pass on top of `lib.layout_picker` that re-ranks per-slide candidates with a usage-budget bonus (+1.5 for a never-used layout, +0.75 after one use, +0.5 after two, etc.). Eligible-but-overlooked layouts (`vertical-bullets`, `pyramid`, `funnel`, `four-column-cards`, …) now surface across long decks instead of the same two or three winners repeating. The bonus is calibrated below the role-match weight (+3), so a strong affinity match still wins on the first use; coverage only kicks in among co-eligible candidates. Singleton layouts (`agenda`, `end`, `full-bleed-cover`) are exempt. Each skeleton slide records the picker + budget rationale under `_meta.layout_rationale` for debugging. Smoke test on a 17-slide mixed deck went from ~7 distinct layouts (baseline) to 15. Covered by `tests/test_layout_budget.py` (14 tests pinning both halves of the contract: spreads usage across co-eligible layouts; never overrides a strong affinity match like a `risk-matrix` fingerprint).

### Changed (repo layout)
- Examples moved from repo-root `examples/feinschliff/` into the plugin folder: `feinschliff/examples/`. Per-brand preview folders renamed from `template-preview-{brand}/` to just `{brand}/` so a GitHub user landing on the plugin sees `examples/spotify/`, `examples/bmw/`, etc. — the brand IS the folder name. The eponymous Feinschliff preview lives at `feinschliff/examples/feinschliff/`. The repo root no longer carries an `examples/` directory.

### Added
- Four new `feinschliff` brand packs derived from getdesign.md, each with a generic non-trademarked glyph and a stable PDF preview committed to `feinschliff/examples/{brand}/`:
  - **Spotify** — Spotify-green accent on true-black canvas, geometric sans, three-bar equalizer glyph.
  - **Binance** — Binance-yellow accent on crypto-black, IBM Plex Sans tabular, four-segment diamond glyph.
  - **BMW** — corporate-blue accent on pure-white canvas, condensed grotesque, quartered-disc glyph (generic pie geometry, not the BMW roundel).
  - **Ferrari** — Rosso Corsa + Modena-yellow on cinematic black, classical serif/sans pairing, heraldic-shield silhouette (the Cavallino Rampante is intentionally not reproduced).

### Changed
- **BMW pack** elevated from token-swap to first reference brand pack with **brand-specific design language**, derived from the canonical [getdesign.md/bmw](https://getdesign.md/bmw/design-md) DESIGN.md. Five new policy blocks shipped alongside DTCG tokens — `layout`, `cover`, `section-marker`, `photography`, `headline-rule`, `chip-rule` — plus an explicit `chip-rule` for the iconic "LEARN MORE ›" inline CTA. Renderer changes to give the deck visible BMW DNA:
  - Light canvas + dark navy hero band rhythm (was dark-canvas-first).
  - 700 / 300 weight ladder with weight 500 explicitly absent (the BMW editorial signature).
  - All display tracking forced to 0; Apple-style negative letter-spacing removed (off-brand for BMW Type Next).
  - 4px M-stripe primitive (`add_m_stripe`) used at chapter dividers and cover boundaries.
  - "LEARN MORE ›" chevron-link primitive (`add_chevron_link`) — UPPERCASE 1.5px tracked.
  - 1px hairline divider primitive (`add_hairline`).
  - Cover, both chapters, and KPI grid rebuilt to BMW-canonical compositions (HairlineHeader cover, M-stripe chapter dividers, spec-cell KPI pattern).
  - Quote and End slides moved off forbidden full-bleed BMW Blue onto compliant dark navy / mirrored cover treatments.
- New radius-aware primitive `add_rounded_rect(radius_px=…)` plumbed through `add_button` / `add_chip` / `add_column(as_card=True)`. Reads from new `radius.btn`, `radius.chip`, `radius.card` token slots so brand packs flip pill / rounded / sharp shapes by editing tokens, never the renderer. BMW (radius=0) falls through to the existing `MSO_SHAPE.RECTANGLE` path — output is pixel-identical to the prior frozen build (verified by per-page PNG diff).
- **Spotify pack** elevated to the second reference brand pack, demonstrating the policy-driven architecture in its mirror-opposite mode from BMW (pills + rounded cards + heavy shadows + dark canvas, vs. BMW's sharp rectangles + hairlines + light canvas). Same primitive set, different token values:
  - `radius.btn = radius.chip = 9999` → fully-rounded pill buttons; `radius.card = 8` → 8px rounded album-art card register. BMW's `add_button` / `add_chip` / `add_column(as_card)` produce pills here without a renderer change.
  - `add_rounded_rect` extended with a `shadow="elevated"|"dialog"` parameter that injects OOXML drop shadows per Spotify DESIGN.md §6 — `rgba(0,0,0,0.3) 0px 8px 8px` for cards, `rgba(0,0,0,0.5) 0px 8px 24px` for modals. Spotify needs heavy shadows on the dark canvas; BMW (no shadows ever) ignores the parameter via the existing `shadow.inherit = False` default.
  - New chrome primitive `add_equalizer_marker` — three-to-four green pill bars of varying height, replacing BMW's `add_m_stripe` role at chapter dividers.
  - New chrome primitive `add_pill_link` — UPPERCASE 1.4px-tracked label voice for inline pill-density CTAs (Spotify analog of BMW's `add_chevron_link`).
  - Bold/regular weight binary (700/400) replaces BMW's 700/300 ladder — the binary IS the typographic hierarchy per DESIGN.md.
  - Cover (album-art shelf + green PLAY pill), both chapters (equalizer marker + soft chapter watermark), KPI grid (4-up rounded shadowed cards on dark canvas), Quote, and End layouts rebuilt as Spotify-canonical compositions. Title Accent and End slides moved off forbidden full-bleed Spotify Green onto dark canvas with green pill CTAs.
  - Six new policy blocks (`layout`, `cover`, `section-marker`, `photography`, `headline-rule`, `chip-rule`, `shadow`) — same shape as BMW's, different values. Confirms the architecture generalizes.
- **Ferrari pack** elevated to the third reference brand pack — cinematic editorial register, sharp 0px corners, single sans family at 500/400/700 weights. Distinct from both BMW (light canvas, 700/300 ladder, M-stripe) and Spotify (pills + heavy shadows, 700/400 binary, equalizer marker):
  - Tokens rebuilt against canonical [getdesign.md/ferrari](https://getdesign.md/ferrari/design-md): Rosso Corsa `#DA291C` (was `#FF2800` placeholder), near-black canvas `#181818` (slightly warm, never pure black), single FerrariSans / Inter family across every text role (was an off-brand serif/sans pair).
  - Display weight is 500 (medium), NEVER bold — DESIGN.md is explicit: *"Don't bold display copy. The cinematic photography does the visual heavy-lifting."* Bold (700) is reserved for component titles, button labels, and the `number-display` (KPI value + race-position cell).
  - Negative letter-spacing on display is the brand's editorial signature — `headline-rule.tracking-em = -0.02` (-1.6px @ 80px display-mega). BMW says no negative tracking; Ferrari says yes.
  - Sharp 0px corners on every CTA, card, band — `radius.btn = radius.card = 0`. Same code path that produces BMW's rectangles produces Ferrari's; opposite of Spotify's pills. Pill geometry (`radius.chip = 9999`) reserved for the badge-pill — the ONE place pill is allowed.
  - New chrome primitive `add_livery_band` — full-width Rosso Corsa accent band, replacing BMW's `add_m_stripe` role and Spotify's `add_equalizer_marker` role at chapter dividers.
  - New chrome primitive `add_uppercase_link` — UPPERCASE 1.4px-tracked button-voice inline link, NO terminator (DESIGN.md is explicit — labels end at the last letter, never with `›` or `→`).
  - New chrome primitive `add_hairline` — 1px brightness-step divider on dark (`#303030` — same hex as canvas-elevated, reads as a tone-step). Ferrari has no shadow tiers; depth comes from hairlines + brightness-step + cinematic photography ONLY.
  - Cover (`title_ink` cinematic dark + Rosso Corsa CTA), accent cover (`title_orange` 60/40 dark/livery-band split), both chapters (chapter_ink 50/50 cinema-photo split, chapter_orange livery-band rule), KPI grid (4-up spec-cell pattern with one cell highlighted in Rosso Corsa as `race-position-cell`), Quote (display-mega 500/-0.02 pull quote), and End (cinematic dark + centered "Grazie." + Rosso Corsa CTA) layouts rebuilt as Ferrari-canonical compositions.
  - Seven new policy blocks (`layout`, `cover`, `section-marker`, `photography`, `headline-rule`, `chip-rule`, `shadow`) — same shape as BMW/Spotify, with `shadow.elevated = "none"` confirming the architecture supports a "shadow-free" brand alongside Spotify's heavy-shadow brand.
  - Heraldic-shield glyph kept (generic abstraction, not the licensed Cavallino Rampante); wordmark continues as "FERRARI" UPPERCASE per the brand's classical lockup register.
- **Binance pack** elevated to the fourth reference brand pack — Binance Yellow on deep crypto-black, BinanceNova / BinancePlex stack with strict numeric-vs-copy split, trading-up green / trading-down red as semantic price-direction tokens, light footer reset on a dark page. Distinct from BMW / Spotify / Ferrari by leaning into the brand's product-DNA chrome (markets-ticker card + Arena Gradient hero) instead of editorial geometry:
  - Tokens rebuilt against canonical [getdesign.md/binance](https://getdesign.md/binance/design-md): accent corrected from the active-state `#F0B90B` placeholder to the brand-defining `#FCD535`. Trading-up `#0ECB81` and trading-down `#F6465D` promoted to first-class semantic tokens — never decorative, never repurposed for generic success / error.
  - Default DISPLAY weight is **600** (semibold), hero / brand-claim headlines lift to 700. Body 400. The trading-platform "this number must read at a glance" register: Binance never softens display weight to 400 the way Airtable or Stripe does.
  - Numeric / copy split is enforced: every price, percentage, KPI value, axis tick renders in BinancePlex (`T.FONT_MONO`); every headline / paragraph / nav label renders in BinanceNova (`T.FONT_DISPLAY`). Mixing them is a system violation per DESIGN.md.
  - Three new chrome primitives, the bespoke Binance vocabulary that earns the elevation:
    - `add_signup_pill` — large yellow pill (radius 9999), bold ink uppercase label, 1.4px tracking. The "this is THE action" CTA, reserved for cover / chapter / end.
    - `add_ticker_row` — single 5-column markets row (32×32 colored coin disc + pair symbol + BinancePlex price + green/red 24h % cell with ▲/▼ glyph + chevron). The product-DNA chrome — same role in the deck as Spotify's album-art tile or Ferrari's livery band.
    - `add_arena_gradient` — vertical yellow→dark linear-gradient band, the Futures Arena product-launch hero treatment. OOXML `gradFill` with explicit yellow-at-0% / surface-dark-at-100% stops.
  - Plus utilities — `add_section_marker` (yellow ▌ 8px-wide vertical bar) replaces BMW's M-stripe role and Spotify's equalizer-marker role at chapter dividers, reads as the trading-pane "active row" indicator. `add_hairline` paints the 1px brightness-step divider in `fog` (same hex as `surface-card-dark` so the divider feels like a surface step, not an ink line). `add_rounded_rect` ported from Spotify; Binance's `radius.btn = 6` / `radius.card = 12` / `radius.pill = 9999` register sits between BMW's sharp 0 and Spotify's full pill.
  - Two bespoke title layouts — the **Markets-Hero** cover (`title_ink`: 50/50 split with hero headline + signup pill on the left and a 5-row markets-table-card on the right with two ▲ green and one ▼ red ticker rows) and the **Arena Gradient** hero (`title_orange`: full-bleed yellow→dark gradient, BinancePlex prize-pool number, centred yellow signup pill). The Markets-Hero is the slide that says "this is Binance" the moment it opens.
  - End slide carries Binance's most distinctive layout choice — the **light footer reset** (`#FAFAFA`, 80px) closes the dark canvas with a "marketing reset" surface, mirroring DESIGN.md `footer-light`. KPI grid rebuilt as 4-up trust-badge cards (yellow BinancePlex value, UPPERCASE muted label, optional green ▲ / red ▼ trading-direction delta). Components Showcase reskinned to display the Binance UI vocabulary — pill pair, BUY/SELL trading chips, trust badge, miniature markets-ticker.
  - Seven new policy blocks (`layout`, `cover`, `section-marker`, `photography`, `headline-rule`, `chip-rule`, `shadow`) — same shape as BMW / Spotify / Ferrari. `shadow.elevated = "none"` (Binance is shadow-free, like Ferrari, opposite of Spotify): depth comes from contrast between `surface-dark` (#0B0E11) and `surface-card-dark` (#1E2329).
  - 4-segment diamond / pinwheel glyph kept (generic abstraction, not the licensed Binance four-rhombus mark); wordmark renders in Binance Yellow per DESIGN.md ("the wordmark uses {colors.primary} for 'BINANCE' type").

## [0.1.0] — 2026-05-01

### Added
- Initial public release.
- **`feinschliff`** plugin (anchor) — brand-pluggable design system that turns Claude Design HTML into brand-perfect PowerPoint decks. Ships with the eponymous `feinschliff` brand pack (indigo palette + Noto Sans, MIT). Three skills: `/deck`, `/extend`, `/compile`.
- Marketplace skeleton: LICENSE (MIT), NOTICE, CONTRIBUTING (DCO), CODE_OF_CONDUCT, SECURITY.
- GitHub: 12 topics, branch protection, issue/PR templates, DCO check, CI workflow.

[Unreleased]: https://github.com/marsmike/feinschmiede/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/marsmike/feinschmiede/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/marsmike/feinschmiede/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/marsmike/feinschmiede/releases/tag/v0.1.0
