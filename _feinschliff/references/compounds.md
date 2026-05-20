# Standard compound catalog

The toolkit ships a small set of compounds that every brand inherits
without needing to redeclare. Brands may override any by shipping a
same-named compound under `brands/<brand>/compounds/`.

## Toolkit-standard (`feinschliff/compounds/`)

### `card(x, y, w, h, counter, heading, body)`

One column in a multi-column-cards layout. Paper-fill background, 40px
internal padding, `col-num` counter / `col-title` heading (36px medium)
/ `col-body` body.

Used by: `two-column-cards`, `key-takeaways`.

### `card-q(x, y, w, h, counter, heading, body)`

Quarterly variant of `card` with a 28px col-title (`col-title-q`) for
narrower 4-column grids.

Used by: `four-column-cards`.

### `kpi-cell(x, y, w, h, value, unit, label, delta)`

One cell of a KPI grid. Top/right/bottom hairlines + large `kpi-value`
display + small `kpi-unit` suffix + `kpi-key` label + `kpi-delta` line.

Used by: `kpi-grid`. The unit is placed at a fixed offset from `x`
(`x+220`); long values may overlap.

### `agenda-item(x, y, w, counter, title, description)`

One row of the agenda list. Top hairline + mono counter + medium
title + graphite description. Hairline + content suppressed via `if:`
when `title` is empty (trailing-row clean-up).

Used by: `agenda`.

### `mck-head(tracker, kicker, action_title)`

Shared MCK-style header: small `tracker` right-aligned, mono caps
`act-kicker`, big 56px `act-title`.

Used by: `action-title`, `horizontal-bullets`, `vertical-bullets`,
`key-takeaways`, `executive-summary`, `v-model`, and most MCK-genre
layouts.

## Brand-required (`brands/<brand>/compounds/`)

Every brand pack must ship these four compounds with the exact
signatures below. Visual treatment is brand-specific.

### `header(pgmeta)`

Top-of-slide chrome. Wordmark + optional gem icon on the left;
right-aligned mono pgmeta line.

### `header-dark(pgmeta)`

Light-text variant of `header` for ink-bg slides (chapter-ink,
title-ink, key-takeaways).

### `footer(left, center, right)`

Bottom chrome — 3 mono-caps columns with a hairline rule above.
Center is typically a date or source stamp.

### `footer-dark(left, center, right)`

Light-text variant of `footer`. Required when the brand uses any
dark-bg layout.

## Brand-specific examples

### `gs-ramspau/compounds/stundenplan-cell(x, y, w, h, text, fill, text_color)`

One cell of a school-schedule grid. `fill` is a token name; rect is
suppressed when empty. Designed to render subject codes with
data-driven highlighting (wiese for accent subjects, tief for sports).

### `gs-ramspau/compounds/termin-row(y, day, when, title, place, day_color, row_fill, highlight)`

One row of a calendar list. Highlight rows get a paper-2 background
fill + wiese day color + accent HIGHLIGHT pill (pill rendered only
when `highlight` is truthy).

## Authoring guidelines

- **Conditional rendering.** Use `if:VALUE` on rect/text/picture nodes
  to suppress emission when `VALUE` is empty. This is the only
  conditional in the DSL.
- **Defaults.** Unbound compound parameters default to empty string;
  pair with `if:` to make slots truly optional.
- **Arithmetic.** Compound bodies can compute positions with
  `{{ x+w-1 }}` style expressions — useful for hairlines along an
  edge or fan-out card grids.
- **Style overrides.** Pass `color:TOKEN` on a text node to override
  the style bundle's default color without authoring a new bundle.

See [`../docs/dsl-grammar.md`](../docs/dsl-grammar.md) for the full
primitive grammar.
