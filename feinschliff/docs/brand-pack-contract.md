# Brand-pack contract (v2)

A brand pack is a directory that `feinschliff` discovers at build time and
uses to resolve colors, fonts, sizes, layouts, and compounds.

Full schema: [`feinschliff/schemas/tokens.schema.json`](../feinschliff/schemas/tokens.schema.json).

## Directory structure

```
<brand-name>/
├── tokens.json        # required — color, font-family, font-size tokens
├── DESIGN.md          # optional — narrative + extends: frontmatter
├── assets/            # optional — gem icons, illustrations
├── layouts/           # optional — brand-local .slide.dsl overrides/additions
└── compounds/         # optional — brand-local .dsl compound overrides/additions
```

At minimum, a brand directory must contain `tokens.json` or `DESIGN.md`.

## tokens.json

Follows the [DTCG draft-2](https://design-tokens.org) format.
Required top-level groups:

| Group | Purpose | Example value |
|---|---|---|
| `color` | Named hex colors | `"accent": { "$value": "#C9A24A" }` |
| `font-family` | Named font stacks | `"display": { "$value": ["Noto Sans", "sans-serif"] }` |
| `font-size` | Named dimensions | `"display": { "$value": "160px" }` |

Optional groups: `font-weight`, `slide` (canvas dimensions), `typography`,
`picture_treatment`, `locale`, `chart`, `brief_defaults`, `$image_provider`.

Plain string values (`"accent": "#C9A24A"`) and DTCG objects
(`"accent": { "$value": "#C9A24A" }`) are both accepted.

## Inheritance

`DESIGN.md` frontmatter may declare `extends: <parent-brand>`. The pipeline
deep-merges the parent's tokens so the child only redefines what it changes.

## Layout naming convention

Toolkit layouts: `<name>.slide.dsl` (e.g. `title-orange.slide.dsl`).
Brand-local overrides live in `<brand>/layouts/` with the same filename.
Brand-local files take precedence over the toolkit when names collide.

## Compound naming convention

Toolkit compounds: `<name>.dsl` (e.g. `header.dsl`).
Brand-local overrides live in `<brand>/compounds/` with the same filename.

Required brand compounds: `header.dsl`, `footer.dsl`.
Required for dark-background layouts: `header-dark.dsl`, `footer-dark.dsl`.

## Discovery sources

Sources are checked in priority order (first match wins):

1. **bundled** — `brands/` shipped inside the `feinschliff` plugin
2. **plugin** — `brands/` directory in any installed Claude Code plugin
3. **env** — directories listed in `FEINSCHLIFF_BRAND_PATH` (colon-separated)
4. **cwd-dev** — `feinschliff/brands/` found by walking up from `$CWD`
5. **user** — `~/.feinschliff/brands/`

## Distribution

Distribute a brand pack by:

- Shipping it as a Claude Code plugin with a `brands/` directory
  (discovery source 2 above picks it up automatically on install).
- Setting `FEINSCHLIFF_BRAND_PATH=/path/to/your/brands` in the shell
  (discovery source 3 — useful for local / private packs).
