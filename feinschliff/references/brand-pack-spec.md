# Brand-pack contract (v2)

A Feinschliff brand pack is a directory under `feinschliff/brands/`
that conforms to this contract. The pipeline (`feinschliff build`,
`feinschliff deck build`, `feinschliff verify`) reads the active brand
at runtime; active brand resolves via `--brand <name>` flag,
`FEINSCHLIFF_BRAND` env-var, or default `feinschliff`.

For the v1 contract (catalog.json + frozen `.pptx` templates per
brand) see the deleted `pre-v0.3` history — that path is retired.

## Required files

```
feinschliff/brands/<brand-name>/
├── DESIGN.md              ← narrative + frontmatter (extends?, palette description, …)
└── tokens.json            ← runtime palette, fonts, sizes, asset_sources
```

At minimum, a brand pack must contain `tokens.json` (and/or
`DESIGN.md`). Discovery (`feinschliff brand list`) picks dirs that
have at least one of `tokens.json`, `DESIGN.md`.

## Optional files

```
feinschliff/brands/<brand-name>/
├── compounds/             ← brand-specific compounds (header, footer, custom marks)
├── layouts/               ← brand-specific layouts (override toolkit or add new)
├── assets/                ← gem icons, illustrations, custom imagery
└── claude-design/         ← human-authored HTML design source
```

Compounds and layouts are inherited from the toolkit by default; the
brand provides only what it overrides or adds. Asset paths inside
`.slide.dsl` files (e.g. `picture 100,52 22x26 path:gem.png`) resolve
against `brands/<brand>/assets/`.

## tokens.json schema

The format follows the [Design Tokens Community Group draft-2 spec](https://design-tokens.org).
Required top-level keys:

```jsonc
{
  "$schema": "https://schemas.designtokens.org/draft-2/format.json",
  "$description": "Human-readable summary of the brand.",
  "color":        { "$type": "color",      "<name>": { "$value": "#RRGGBB" } },
  "font-family":  { "$type": "fontFamily", "display": { "$value": [...] }, … },
  "font-weight":  { "$type": "fontWeight", "regular": { "$value": 400 }, … },
  "font-size":    { "$type": "dimension",  "display": { "$value": "160px" }, … },
  "slide":        { "$type": "dimension",  "width": { "$value": "1920px" }, … },
  "asset_sources":{ "default": { "kind": "static" } }
}
```

The toolkit style bundles (declared in
[`lib/dsl/tokens.py`](../lib/dsl/tokens.py)) reference these tokens by
name. Brands MUST supply every named color and font-size the toolkit
layouts touch (or inherit them — see "Inheritance" below).

### Required color tokens

`accent`, `accent-hover`, `highlight`, `ink`, `black`, `graphite`,
`steel`, `silver`, `fog`, `paper`, `paper-2`, `off-white`,
`off-white-2`, `rule-dark`, `white`.

### Required font-size tokens

`display`, `display-xl`, `huge`, `title-l`, `slide-title`, `sub`,
`body`, `eyebrow`, `footer`, `pgmeta`, `kpi-value`, `kpi-unit`,
`kpi-key`, `kpi-delta`, `agenda-num`, `agenda-t`, `agenda-d`,
`col-num`, `col-title`, `col-title-q`, `col-body`, `btn`, `chip`,
`bar-label`, `bar-num`, `quote`, `quote-attr`, `bignum`, `act-title`,
`act-kicker`, `tracker`, `h-idx`, `h-hd`, `h-li`, `lede`.

### Required font-family tokens

`display`, `body`, `mono`.

### asset_sources

```jsonc
"asset_sources": {
  "default": { "kind": "static" },
  "<source_id>": {
    "kind": "static" | "search",
    "base_url": "https://…",
    "auth":     { "type": "header_token", "env": "FOO_API_KEY", "header": "Authorization", "format": "Bearer {token}" }
  }
}
```

`static` means catalog-bundled assets only. `search` declares a CDN
the resolver can query (Unsplash, Iconify, Wikimedia, etc.).

## Image provider

Optional. A brand may declare a build-time image provider so that the
`picture` primitive can resolve images by **query** instead of by
filesystem path. The provider hook is opt-in — brands that omit
`$image_provider` are unaffected, and `picture path:"..."` keeps working
as it always has.

```jsonc
{
  "$image_provider": {
    "kind":   "unsplash",
    "config": { "access_key": "${env:UNSPLASH_ACCESS_KEY}" }
  }
}
```

- **`kind`** — name of a registered provider. Built-ins live under
  `lib/providers/`; out-of-tree providers ship as plugin files (see
  [`image-providers.md`](image-providers.md) for discovery rules).
- **`config`** — provider-specific dict passed through to the provider
  constructor. Schema is opaque to the toolkit.

When a brand declares `$image_provider`, slides may write:

```
picture 320,200 1280x720 query:"morning kitchen light"
```

At build time the active provider's `search(query)` resolves to an
`ImageHit`; the URL is materialised into `<deck_dir>/.cache/` and pinned
in `<deck_dir>/asset_lock.json` so rebuilds are deterministic.
`query:` and `path:` are mutually exclusive on a single `picture` node.

### Inheritance through `extends`

`$image_provider` is inherited via the `extends:` chain — a child brand
that lives on top of a parent with a configured provider picks it up
automatically. The merge rules are:

- **`config` is deep-merged** when child and parent both target the same
  `kind` (the child only refines specific keys).
- **`kind` is fully replaced** when the child swaps it; the parent's
  `config` is dropped because it was scoped to a different provider.

### Worked example — built-in `unsplash`

```jsonc
{
  "$image_provider": {
    "kind":   "unsplash",
    "config": { "access_key": "${env:UNSPLASH_ACCESS_KEY}" }
  }
}
```

`UnsplashProvider` reads `access_key` from `config` first, falls back to
the `UNSPLASH_ACCESS_KEY` env var, and runs in **stub mode** (returns
`[]`, emits one warning per process) when neither is set so OSS builds
without a key still complete.

### Worked example — downstream plugin provider

A downstream Claude Code plugin can ship its own provider without
patching upstream. For example, an internal brand backed by a curated
design-kit mirror (the `feinschliff-bsh` plugin's `bsh-designkit`)
declares:

```jsonc
{
  "$image_provider": {
    "kind":   "bsh-designkit",
    "config": { "kit_root": "/srv/bsh/designkit" }
  }
}
```

The provider class lives in the plugin under
`feinschliff_providers/bsh_designkit.py`; the upstream toolkit discovers
it on every build and looks it up by `kind`. See
[`image-providers.md`](image-providers.md) for the discovery rules and
the authoring contract.

## Inheritance via DESIGN.md frontmatter

```yaml
---
version: 1.0
name: My Brand
extends: feinschliff
description: "…"
---
```

`extends: <parent>` flattens the parent brand's tokens into the
child's at load time. The child overrides only the tokens it
redefines (typically `color` + `font-family`). Useful when a brand
shares the toolkit's size system but swaps the palette.

## Brand-specific compounds

The toolkit's 39 layouts call two compounds that every brand must
ship: `header` and `footer`. If the brand also uses any of the
toolkit's dark-mode layouts (chapter-ink, title-ink, key-takeaways)
it must additionally ship `header-dark` and `footer-dark`.

```
brands/<brand>/compounds/
├── header.dsl              # logo + pgmeta at top of slide
├── header-dark.dsl         # light variant for ink-bg slides
├── footer.dsl              # bottom chrome (left/center/right)
└── footer-dark.dsl         # light variant for ink-bg slides
```

The signature is fixed:

```
compound header(pgmeta): …
compound header-dark(pgmeta): …
compound footer(left, center, right): …
compound footer-dark(left, center, right): …
```

Other compounds are optional brand additions. See
[`compounds.md`](compounds.md) for the toolkit catalog.

## Brand-specific layouts

A brand may add or override layouts at `brands/<brand>/layouts/`. The
build pipeline accepts an explicit path; layouts in the brand's dir
take precedence over the toolkit's when both exist (`feinschliff
brand inspect <brand>` reports which override).

## Inspect / list

```
$ feinschliff brand list
  → 17 brands × {tokens, design, +layouts?, +compounds?}

$ feinschliff brand inspect <brand>
  brand: <name>
  tokens.json: 24 colors, 4 font families, 37 sizes
  asset_sources: default
  layouts: 33 (33 inherited, 0 overridden, 0 brand-only)
  compounds: 4 (footer, footer-dark, header, header-dark)
```

## Sibling references

- [`compounds.md`](compounds.md) — toolkit-standard compound catalog
- [`image-providers.md`](image-providers.md) — `$image_provider` ABC + authoring guide
- [`../docs/dsl-grammar.md`](../docs/dsl-grammar.md) — `.slide.dsl` reference
- [`../docs/port-your-brand.md`](../docs/port-your-brand.md) — end-to-end tutorial
