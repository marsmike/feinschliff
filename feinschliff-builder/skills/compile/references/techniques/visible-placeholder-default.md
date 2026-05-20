# Empty picture path → visible placeholder, not silent skip

## Pattern
When `picture X,Y WxH path:""` (empty path), the default behavior used to
be "silently skip the primitive". This made missing assets INVISIBLE
during render — the slide just had a hole where the picture should be,
and you'd discover it only when the user pointed it out.

## Fix shape
When path is empty (or resolves to a non-existent file), emit a
`paper-2 + fog stroke` placeholder rect at the picture's bbox. The
absence becomes visible at review time, not at deployment time.

## For `feinschliff:compile`
Every brand pack should ship with this behavior baked into the picture
primitive emitter. It's a one-line change that dramatically improves the
dev loop: "I forgot to wire the asset" turns into a visible grey box
that even a screenshot review will catch.

## Evidence
- Before: cover-illustration with empty `illustration:` rendered an
  invisible right half. Looked correct at thumbnail.
- After: same case shows a grey rect at the picture position. Three
  iterations into the brand pack we noticed all four cover variants
  had empty placeholders and fixed them in batch.
