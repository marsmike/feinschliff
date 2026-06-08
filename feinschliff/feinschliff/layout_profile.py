"""Layout-affinity profiles parsed from ``.slide.dsl`` frontmatter.

Every layout carries its picker-affinity profile as a YAML frontmatter
fence at the top of its ``.slide.dsl`` file::

    ---
    role: data-quantity
    ideal_count: [2, 4]
    data_band: kpi          # none | kpi | table | chart
    comparison: false
    narrative_role: ...      # optional
    narrative_act: ...       # optional: situation | complication | resolution
    time_axis_role: ...      # optional: strategic | chronological | tactical
    diagram_complexity: ...  # optional: simple | medium | deep
    variety_exempt: false    # optional, default false
    when_not_to_use:         # optional
      - narrative_role=closing
    ---
    # human-readable header comment continues…
    canvas 1920x1080
    …

The profile lives *next to the layout it describes* — a single source of
truth. :func:`build_profile_table` parses the discovered layout set into the
``{name: profile}`` table consumed by :mod:`feinschliff.layout_picker`,
replacing the old hand-maintained ``_LAYOUTS`` dict. Because the table is
derived from whatever :func:`feinschliff.layout_discovery.discover_layout_paths`
finds, the picker's universe is the on-disk universe by construction — a
layout can never exist on disk yet be unpickable.

The internal profile dict mirrors the keys the picker's scoring loop reads:
``role``, ``ideal_count`` (tuple), ``data``, ``comp``, plus the optional
``narrative_role`` / ``narrative_act`` / ``time_axis_role`` /
``diagram_complexity`` / ``when_not_to_use`` / ``variety_exempt`` fields.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from feinschliff.dsl.parser import split_frontmatter

# Declared-value enums (the values a layout may *declare* in its profile).
# Kept local so this module does not import the picker (which imports us).
_VALID_DATA_BANDS = frozenset({"none", "kpi", "table", "chart"})
_VALID_NARRATIVE_ACTS = frozenset({"situation", "complication", "resolution"})
_VALID_TIME_AXIS_ROLES = frozenset({"strategic", "chronological", "tactical"})
_VALID_DIAGRAM_COMPLEXITY = frozenset({"simple", "medium", "deep"})

# Frontmatter key → internal profile key. The picker scoring loop reads the
# internal names (`data`, `comp`); the frontmatter uses the clearer external
# names (`data_band`, `comparison`).
_REQUIRED_KEYS = ("role", "ideal_count", "data_band", "comparison")
_OPTIONAL_STR_KEYS = {
    "narrative_role": "narrative_role",
    "narrative_act": "narrative_act",
    "time_axis_role": "time_axis_role",
    "diagram_complexity": "diagram_complexity",
}


class ProfileError(ValueError):
    """A layout's frontmatter profile is missing or malformed."""


def parse_profile(frontmatter_text: str, *, source: str) -> dict:
    """Parse one frontmatter YAML block into an internal profile dict.

    Raises :class:`ProfileError` with *source* context on any schema
    violation — required key missing, wrong type, or out-of-enum value.
    """
    try:
        raw = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError as exc:  # pragma: no cover - defensive
        raise ProfileError(f"{source}: invalid YAML frontmatter: {exc}") from exc
    if not isinstance(raw, dict):
        raise ProfileError(f"{source}: frontmatter must be a YAML mapping")

    for key in _REQUIRED_KEYS:
        if key not in raw:
            raise ProfileError(f"{source}: frontmatter missing required key {key!r}")

    profile: dict = {}

    role = raw["role"]
    if not isinstance(role, str) or not role:
        raise ProfileError(f"{source}: 'role' must be a non-empty string")
    profile["role"] = role

    ideal = raw["ideal_count"]
    if (
        not isinstance(ideal, (list, tuple))
        or len(ideal) != 2
        or not all(isinstance(n, int) for n in ideal)
        or ideal[0] > ideal[1]
    ):
        raise ProfileError(
            f"{source}: 'ideal_count' must be [lo, hi] integers with lo<=hi, got {ideal!r}"
        )
    profile["ideal_count"] = (int(ideal[0]), int(ideal[1]))

    data_band = raw["data_band"]
    if data_band not in _VALID_DATA_BANDS:
        raise ProfileError(
            f"{source}: 'data_band' {data_band!r} not in {sorted(_VALID_DATA_BANDS)}"
        )
    profile["data"] = data_band

    comparison = raw["comparison"]
    if not isinstance(comparison, bool):
        raise ProfileError(f"{source}: 'comparison' must be a boolean, got {comparison!r}")
    profile["comp"] = comparison

    # Optional string-enum fields. Empty/absent → omitted (stays neutral in
    # scoring, matching the legacy "field not present" contract).
    enum_map = {
        "narrative_act": _VALID_NARRATIVE_ACTS,
        "time_axis_role": _VALID_TIME_AXIS_ROLES,
        "diagram_complexity": _VALID_DIAGRAM_COMPLEXITY,
    }
    for fm_key, prof_key in _OPTIONAL_STR_KEYS.items():
        if raw.get(fm_key) in (None, ""):
            continue
        val = raw[fm_key]
        if not isinstance(val, str):
            raise ProfileError(f"{source}: {fm_key!r} must be a string, got {val!r}")
        allowed = enum_map.get(fm_key)
        if allowed is not None and val not in allowed:
            raise ProfileError(
                f"{source}: {fm_key!r} {val!r} not in {sorted(allowed)}"
            )
        profile[prof_key] = val

    wntu = raw.get("when_not_to_use")
    if wntu is not None:
        if not isinstance(wntu, list) or not all(isinstance(r, str) for r in wntu):
            raise ProfileError(f"{source}: 'when_not_to_use' must be a list of strings")
        profile["when_not_to_use"] = wntu

    if "variety_exempt" in raw:
        ve = raw["variety_exempt"]
        if not isinstance(ve, bool):
            raise ProfileError(f"{source}: 'variety_exempt' must be a boolean")
        profile["variety_exempt"] = ve

    return profile


def load_profile(path: Path) -> dict:
    """Read a ``.slide.dsl`` file and return its internal profile dict.

    Raises :class:`ProfileError` when the file has no frontmatter fence or
    the fence fails validation.
    """
    text = path.read_text(encoding="utf-8")
    fm, _ = split_frontmatter(text)
    if fm is None:
        raise ProfileError(
            f"{path}: no '--- … ---' frontmatter profile. Every layout must "
            f"declare its picker affinity (role / ideal_count / data_band / "
            f"comparison) so the picker can rank it."
        )
    return parse_profile(fm, source=str(path))


def build_profile_table(
    paths: dict[str, Path], *, strict: bool = True
) -> dict[str, dict]:
    """Build the ``{name: profile}`` picker table from discovered layouts.

    *paths* maps layout name → ``.slide.dsl`` path (already resolved for
    source/brand precedence by the caller).

    When *strict* (the default), a missing/invalid profile raises
    :class:`ProfileError` — the toolkit's own layouts must all be pickable.
    When ``strict=False``, an unparseable layout is skipped (it simply won't
    be a pick candidate); used by tolerant runtime callers that would rather
    drop one third-party layout than fail the whole deck build.
    """
    table: dict[str, dict] = {}
    for name, path in paths.items():
        try:
            table[name] = load_profile(path)
        except ProfileError:
            if strict:
                raise
    return table
