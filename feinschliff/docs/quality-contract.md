# Feinschliff Quality Contract

This document is the single source of truth for what makes a deck pass
or fail. Every CLI entrypoint (`build`, `deck build`, `deck polish`,
`verify`, `verify-quality`, `ship`) consumes this contract.

## Defect dataclass

`lib.defects.Defect(slide_index, kind, severity, message, meta)` —
immutable, JSON-serializable.

## Kinds

(see `feinschliff/lib/defects.py:DefectKind` for the canonical enum)

> Source modules tagged "(Task N)" or "(planned)" are forward references
> introduced by later tasks in the quality-system plan, not present on
> the current commit. Every untagged source module exists today.

| Kind                       | Layer      | Source module                  |
|----------------------------|------------|--------------------------------|
| text-overlap               | geometry   | lib.layout_validator           |
| out-of-bounds              | geometry   | lib.layout_validator           |
| slot-overflow              | content    | lib.content_validator          |
| diagram-overflow           | diagram    | lib.layout_validator           |
| diagram-text-too-small     | diagram    | lib.layout_validator           |
| diagram-color-mismatch     | diagram    | lib.layout_validator           |
| drop-shadow                | chrome     | lib.verify.chrome              |
| gradient-fill              | chrome     | lib.verify.chrome              |
| fat-outline                | chrome     | lib.verify.chrome              |
| chrome-drift               | chrome     | lib.verify.chrome              |
| title-too-long             | content    | lib.content_validator          |
| filler-word                | content    | lib.content_validator          |
| vague-so-what              | content    | lib.content_validator          |
| squint-test                | LLM        | lib.verify.deck.squint         |
| title-body-coherence       | LLM        | lib.verify.deck.title_body     |
| claim-title                | LLM        | lib.verify.llm.rubric (Task 3) |
| bullet-dump                | LLM        | lib.verify.llm.rubric (Task 3) |
| unknown-compound           | dsl        | lib.pipeline                   |
| missing-asset              | asset      | lib.dsl.pptx_emit              |
| placeholder-rectangle      | asset      | lib.verify.assets (planned)    |

## Severity

`fatal` defects exit non-zero by default. `warn` and `info` are reported
but do not block. CLI flags can demote a `fatal` kind to non-blocking on
a per-invocation basis (e.g. `--allow-diagram-warnings` demotes
`diagram-overflow` and `diagram-text-too-small`).

## Adding a kind

1. Add the enum value to `lib.defects.DefectKind`.
2. Add it to `_FATAL` if it should block by default.
3. Update the table above.
4. Emit it from exactly one module (the "Source module" column).
5. Add a test asserting the kind is reachable from at least one CLI.
