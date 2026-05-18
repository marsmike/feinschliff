# Image-provider framework

Reference for the pluggable image-provider abstraction added in the
`image-provider-framework` work. Read this when you want to:

- understand what `$image_provider` on a brand pack actually does,
- ship a custom provider from a downstream Claude Code plugin,
- audit how queries are resolved + pinned at build time,
- or debug why a provider isn't being picked up.

The contract is intentionally small: one ABC, one registry, one
discovery loop. Built-in providers live under
[`../lib/providers/`](../lib/providers/); out-of-tree providers live in
plugins under `~/.claude/plugins/.../feinschliff_providers/`.

## What is an image provider?

An image provider is a Python class that knows how to turn a textual
**query** (e.g. `"morning kitchen light"`) into one or more concrete
image hits (URL + license + attribution + dimensions + MIME). The
toolkit's `picture` DSL primitive grows a `query:` keyword whose
resolution flows through whatever provider the active brand declares.

This exists for two reasons. First, different brand families need
different sources: an OSS brand can lean on Unsplash; an internal brand
must source from an approved design-kit mirror; a research brand may
want a Wikimedia adapter. Second, downstream plugins ship outside the
upstream `feinschliff/` subtree — they need a stable extension seam
that survives every upstream resync. The provider registry is that
seam: any plugin can drop a `.py` file in its
`feinschliff_providers/` directory and the build picks it up.

Brands that don't declare `$image_provider` are unaffected.
`picture path:"..."` keeps working as it always has — only `query:` goes
through the resolver.

## The `ImageProvider` ABC

Lives at [`../lib/image_provider.py`](../lib/image_provider.py).

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class ImageHit:
    """One result row from a provider.search() call.

    `url` is either http(s):// or file:// — the picture-emit step
    materialises both into a local Path before handing to python-pptx.
    """
    url: str
    license: str          # e.g. "Unsplash License", "internal-bsh"
    attribution: str      # human-readable credit line
    width: int | None     # pixels, when known
    height: int | None
    mime: str             # "image/jpeg", "image/svg+xml", ...


class ImageProvider(ABC):
    name: ClassVar[str]

    def __init__(self, config: dict | None = None) -> None:
        self.config = config or {}

    @abstractmethod
    def search(
        self,
        query: str,
        *,
        count: int = 1,
        hints: dict | None = None,
    ) -> list[ImageHit]:
        """Return up to `count` ranked hits for the query string.

        `hints` is reserved for future slot-aware nudges (aspect_ratio,
        dominant_color, slot_role). Implementations may ignore it.
        Returns [] on no match — never raises for misses.
        """
```

Three rules, learned the hard way:

1. **Set `name`** as a class attribute before the `@register_provider`
   decorator runs. It must be unique across all loaded providers.
2. **`search()` returns `[]` on miss; never raises.** The pipeline's
   contract is "no hits → emit placeholder + record `missing_assets`
   entry". An uncaught exception is caught at the `_emit_picture`
   boundary and treated as a search error (separate entry kind), but
   surfacing exceptions to callers is a bug — handle network and parse
   failures inside `search()`.
3. **Stay under the 30 s wall budget.** This is the budget the emitter
   plans for. Wedging on a 10 min request blocks the whole deck build.
   The bundled `UnsplashProvider` uses 14 s per attempt × 2 attempts +
   1 s backoff = 29 s worst case.

`hints` is currently always `None`; the parameter is reserved so the
ABC can grow slot-aware nudges (aspect ratio, dominant color, slot
role) without a breaking signature change.

## Discovery rules

The framework scans for providers across five tiers, in this order:

| Tier      | Where                                                                | When to use                                                       |
|-----------|----------------------------------------------------------------------|-------------------------------------------------------------------|
| bundled   | `lib/providers/*.py`                                                 | Upstream-shipped providers (`unsplash`).                          |
| plugin    | `~/.claude/plugins/.../feinschliff_providers/*.py`                   | Out-of-tree downstream providers. The intended extension point.   |
| env       | `FEINSCHLIFF_PROVIDER_PATH` (`os.pathsep` list of directories)       | Per-shell overrides; tests stage temp dirs via this knob.         |
| cwd-dev   | walk up from `$CWD` until a `.git` boundary                          | In-place development inside a `feinschliff/` checkout.            |
| user      | `~/.feinschliff/providers/*.py`                                      | Personal, machine-local providers.                                 |

`discover_providers()` is idempotent. The CLI (`cli/build.py`,
`cli/deck.py`) calls it once after brand resolution; subsequent calls
are no-ops. Within a tier, files are imported in sorted order.

**First-write-wins.** If two tiers register the same `name`, the
later one's `register_provider` call raises `ValueError` (which the
discovery loop swallows + logs) and the **earlier** definition stays
canonical. Bundled providers are therefore authoritative; plugins
extend rather than override.

**Broken providers don't block unrelated builds.** A plugin file that
fails to import is logged to `pipeline_log` with a truncated
traceback, then skipped. Other plugins and the bundled providers keep
loading.

### Plugin file-layout convention

Out-of-tree providers live at
`~/.claude/plugins/<plugin-name>/feinschliff_providers/<name>.py` (or
the marketplaces variant
`~/.claude/plugins/marketplaces/<mp>/<plugin-name>/feinschliff_providers/<name>.py`).
Both layouts are supported.

Inside the plugin file:

- One `.py` file per provider (multiple per file works, but keep one
  per file for clarity).
- The module is imported as
  `feinschliff_providers._auto.<plugin-slug>_<stem>` — a synthetic
  name that avoids `sys.path` pollution and namespace collisions.
- The plugin's rsync from upstream **must exclude `feinschliff_providers/`**
  so the directory survives every resync.

## Authoring a custom provider

Minimal working example. Drop this at
`~/.claude/plugins/my-plugin/feinschliff_providers/fixture.py`:

```python
"""Tiny fixture provider — returns a single pinned ImageHit."""
from lib.image_provider import ImageHit, ImageProvider, register_provider


@register_provider
class FixtureProvider(ImageProvider):
    name = "fixture"

    def search(self, query, *, count=1, hints=None):
        # Real providers would consult an index / API here. This one
        # just hands back a single file:// hit from config.
        path = self.config.get("path")
        if not path:
            return []
        return [
            ImageHit(
                url=f"file://{path}",
                license="internal",
                attribution="fixture",
                width=None, height=None,
                mime="image/png",
            )
        ]
```

The brand pack then opts in:

```jsonc
{
  "$image_provider": {
    "kind":   "fixture",
    "config": { "path": "/abs/path/to/fixture.png" }
  }
}
```

Authoring checklist:

- [ ] `name` is unique and short (lowercase, hyphens OK).
- [ ] `@register_provider` decorates the class.
- [ ] `search()` swallows all expected failure modes (network,
      parsing, auth) and returns `[]` — never raises.
- [ ] Network providers respect a 30 s wall budget and emit at most
      one warning per process for repeated stub-mode misses.
- [ ] Returned `ImageHit.url` is `http(s)://` or `file://`. Bare paths
      work too (treated as filesystem) but `file://` is preferred for
      explicitness.

## Configuration

A brand pack opts in to provider lookup by declaring `$image_provider`
in its `tokens.json`:

```jsonc
{
  "$image_provider": {
    "kind":   "<registered-name>",
    "config": { /* opaque provider-specific dict */ }
  }
}
```

`kind` is the provider's class-level `name`. `config` is forwarded
verbatim to the provider's `__init__`.

`$image_provider` participates in the `extends:` chain:

- `config` is **deep-merged** when child and parent target the same
  `kind` — a child can refine specific keys without restating the rest.
- `kind` is **fully replaced** when the child swaps it; the parent's
  `config` is dropped (it was scoped to a different provider).

Schema enforcement lives in
[`../lib/schemas/tokens.schema.json`](../lib/schemas/tokens.schema.json)
under `properties.$image_provider`. `additionalProperties: false` —
unknown top-level keys on the block fail validation.

## Picture primitive — query mode

When `$image_provider` is configured, slide DSL can write:

```
picture 320,200 1280x720 query:"morning kitchen light"
picture 320,200 1280x720 query:"team portrait" label:hero
```

Resolution:

1. Derive a stable `slot_id` — from the `label:` if set, otherwise
   slugified from the query (`"Morning kitchen!"` →
   `morning_kitchen`).
2. Read `<deck_dir>/asset_lock.json`. If the lock matches the active
   provider and has a pinned hit for `slot_id` whose URL is still
   resolvable, use it.
3. Otherwise call `provider.search(query, count=1)`. Pin the first
   result; write the lock.
4. Materialise the hit into `<deck_dir>/.cache/<sha1(url)>.<ext>` (for
   `http(s)://`) or verify the path exists (for `file://`).
5. Hand the local path to python-pptx as the picture source.

`query:` and `path:` are **mutually exclusive** on a single picture
node — setting both raises `DSLError` at emit time. A `query:` node
with no provider on the `EmitContext` is a hard error: the brand
author wrote `query:` but forgot to wire `$image_provider`. Failing
loud here is intentional; silent fallback would mask a misconfig that
ships broken decks.

## Lock file — `<deck_dir>/asset_lock.json`

Format (version 1):

```jsonc
{
  "version": 1,
  "provider": "unsplash",
  "slots": {
    "hero_image": {
      "query":       "kitchen morning light",
      "url":         "https://images.unsplash.com/photo-1234?w=1920",
      "license":     "Unsplash License",
      "attribution": "Jane Doe on Unsplash",
      "mime":        "image/jpeg",
      "width":       1920,
      "height":      1280,
      "pinned_at":   "2026-05-18T14:32:11Z"
    }
  }
}
```

Behaviour:

- Lock is **scoped to a provider name**. A brand switch to a different
  `kind` invalidates the whole file and re-pins from scratch.
- Pinned entries are reused on rebuild iff (a) provider matches,
  (b) the recorded `query` matches the slide's query, and (c) the URL
  is still resolvable (`file://` paths are checked on disk; HTTP URLs
  are trusted between rebuilds — no HEAD pre-flight).
- Stale entries (deleted `file://` target, or the lock is from a
  different provider) trigger a re-search and overwrite.
- Writes are atomic (tmp-file + `os.replace`), so an interrupted
  build won't leave a half-written lock that future runs fail to
  parse.
- **Failed searches are not pinned.** A "no results" record would
  block the slot from ever resolving even after the provider's data
  improves.

Delete `asset_lock.json` (or one slot key) to force a re-pin.

## Built-in providers

### `unsplash`

Reference implementation at
[`../lib/providers/unsplash.py`](../lib/providers/unsplash.py).

- **Endpoint.** `GET https://api.unsplash.com/search/photos`.
- **Auth.** `Authorization: Client-ID <access_key>`. Read from
  `config["access_key"]` (preferred) or `UNSPLASH_ACCESS_KEY` env.
- **Stub mode.** When no key is configured, `search()` returns `[]`
  and emits exactly one `RuntimeWarning` per process so OSS builds
  without a key still complete (missing-asset placeholders show where
  photos would land).
- **Retry.** Single retry on 429 / 5xx and network errors. Permanent
  4xx (401, 403, 404, ...) is one-and-done. 30 s total wall budget
  (`14 + 1 + 14 = 29 s`).
- **Output.** Maps each Unsplash result to an `ImageHit` with
  `license="Unsplash License"`, `attribution="<name> on Unsplash"`,
  `mime="image/jpeg"`.

No new dependency — uses stdlib `urllib.request` rather than
`requests`.

## Failure modes

| Condition                                  | Behaviour                                                                                       |
|--------------------------------------------|-------------------------------------------------------------------------------------------------|
| Brand has no `$image_provider`             | Provider step skipped. `query:` raises `DSLError`. `path:` unaffected.                          |
| Provider `kind` unknown                    | `get_provider` raises `KeyError` with the full registry listing. Build aborts before any slide. |
| Provider import error                      | `discover_providers` logs traceback to `pipeline_log` and skips the file. Unrelated builds OK.  |
| `search()` returns `[]`                    | Emit placeholder rect; append `{kind: "no-hit"}` to `missing_assets`. Build aborts unless `--allow-missing-assets`. |
| `search()` raises                          | Caught at `_emit_picture`. Treated like no-hit but tagged `{kind: "search-error"}`.            |
| HTTP download fails (timeout / URLError)   | Single retry; on persistent failure, placeholder rect + `{kind: "fetch-failed"}` entry.        |
| Lock URL no longer resolves                | Re-search via provider; overwrite the lock entry.                                              |
| `query:` + `path:` both set on one node    | `DSLError` at emit time.                                                                        |
| `query:` set but `ctx.image_provider` None | `DSLError` — the brand forgot to wire `$image_provider`.                                       |
| `ctx.deck_dir` unset                       | HTTP downloads use a throwaway tempdir; warns at emit time (no rebuild reuse).                  |

## Related

- [`brand-pack-spec.md`](brand-pack-spec.md) — where `$image_provider`
  sits in the brand-pack contract.
- [`../docs/architecture.md`](../docs/architecture.md) — provider
  lookup step in the pipeline diagram.
- [`../docs/port-your-brand.md`](../docs/port-your-brand.md) — short
  note for new brand authors.
