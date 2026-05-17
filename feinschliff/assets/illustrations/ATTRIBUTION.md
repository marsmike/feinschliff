# Plugin-level shared illustrations

These illustrations are served as the universal placeholder for image
slots whose per-brand asset is missing. The asset resolver
(`lib/dsl/pptx_emit.py`) tries the brand's own `assets/<rel-path>`
first; this directory is the fallback. Any brand can override by
placing a file at the same relative path under its own `assets/` dir.

## placeholder.jpg

AI-generated via **Black Forest Labs Flux 1.1 Pro** on Replicate.

- Prompt: photorealistic close-up of a diamond cutter at work —
  gloved hand with tweezers polishing a faceted brilliant on a
  lapidary grinding wheel, warm sparks bouncing off the diamond's
  facets, sunlit workshop background. The motif matches the brand's
  name ("Feinschliff" = final polish / finishing touch).
- License: synthetic output, no third-party rights attach. Free to use,
  modify, and redistribute under this repo's MIT license.
- 16:9 aspect ratio so it fits every layout's image slot without
  awkward crops.
