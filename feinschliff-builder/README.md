# feinschliff-builder

Brand-pack authoring toolkit for [feinschliff](https://github.com/marsmike/feinschliff).
Compile HTML to DSL, verify deck quality, decompile existing PPTX files, and
iterate brand packs with an AI-assisted verify loop.

**Requires:** `feinschliff` installed first.

## Install

```bash
/plugin marketplace add marsmike/feinschliff   # once per machine
/plugin install feinschliff@feinschmiede        # required dependency
/plugin install feinschliff-builder@feinschmiede
```

## Skills

| Skill | When to use |
|---|---|
| **`/compile`** | Scaffold v2 `.slide.dsl` skeletons from Claude Design HTML output |
| **`/improve-brand`** | Iterate a brand pack's layouts against a source PPTX — runs the verify loop, fans out one sub-agent per layout below threshold |

## CLI subcommands

```bash
feinschliff-builder <subcommand> [options]
```

| Subcommand | What it does |
|---|---|
| `brand` | Brand pack utilities (init, bake, validate tokens.json) |
| `compile-html` | Compile HTML to `.slide.dsl` skeletons |
| `decompile` | Reverse-engineer a `.pptx` into DSL fragments |
| `verify` | Structural validation of a built `.pptx` deck |
| `verify-quality` | LLM quality rubric pass (spacing, contrast, typography) |
| `verify-diagram` | Validate diagram DSL files for syntax and token references |

### Typical authoring workflow

```bash
# Start a new brand from a source PPTX
feinschliff-builder brand init --from-pptx source.pptx --name mybrand

# Decompile to understand what the source used
feinschliff-builder decompile source.pptx --out .debug/decompile/

# Build and verify
feinschliff build layouts/title-orange.slide.dsl --brand mybrand -o /tmp/test.pptx
feinschliff-builder verify /tmp/test.pptx
feinschliff-builder verify-quality /tmp/test.pptx

# Or build + verify + quality in one pass (via feinschliff ship)
feinschliff ship --brand mybrand -o /tmp/test.pptx layouts/title-orange.slide.dsl
```

## Documentation

See the parent repo docs for the full pipeline:
[`docs/brand-pack-contract.md`](../feinschliff/docs/brand-pack-contract.md).

## License

MIT — see repo root [`LICENSE`](../LICENSE).
