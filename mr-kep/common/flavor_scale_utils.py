"""Canonical flavor scale utilities (P95G).

Single source of truth for the layered flavor scale contract
(P95C verdict C / CANONICAL_SCHEMA.md §5):

  Layer 1 — storage/raw   : flavor_evidence            -> 0.0-1.0
  Layer 2 — derived       : canonical_flavor_vectors   -> 0-100
  Layer 3 — presentation  : flavor_profiles            -> 0-100
  Bridge                   : flavor_evidence *100 -> canonical_flavor_vectors

All writers MUST route axis values through these helpers so the storage
layer can never receive a 0-100 value (the bug P95D fixed). No DB access,
no schema changes — pure functions only.
"""

from __future__ import annotations

# Canonical fixed 7-axis contract (CANONICAL_SCHEMA.md).
CANONICAL_AXES = ["smoky", "peaty", "fruity", "sweet", "spicy", "maritime", "sherry"]

STORAGE_MIN, STORAGE_MAX = 0.0, 1.0
PROFILE_MIN, PROFILE_MAX = 0.0, 100.0


def to_storage_scale(value):
    """Map a source axis value to the flavor_evidence storage scale (0.0-1.0).

    Input may be 0-100, 0-1, None, or non-numeric.
      - None / empty / non-numeric -> None
      - already 0-1 (<= 1.0)       -> unchanged
      - 0-100 (> 1.0)              -> divide by 100
      - < 0                        -> clamp to 0
      - > 100                      -> clamp to 1
    Idempotent: a value already in 0-1 is returned unchanged.
    """
    if value is None or value == "":
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f > STORAGE_MAX:
        f = f / 100.0
    if f < STORAGE_MIN:
        f = STORAGE_MIN
    if f > STORAGE_MAX:  # defensive clamp after any future logic change
        f = STORAGE_MAX
    return f


def to_profile_scale(value):
    """Map a source axis value to the derived/presentation scale (0-100 int).

    Input may be 0-1, 0-100, None, or non-numeric.
      - None / empty / non-numeric -> None
      - already 0-100 (> 1.0)      -> unchanged (rounded to int)
      - 0-1 (<= 1.0)               -> multiply by 100 (rounded to int)
      - < 0                        -> clamp to 0
      - > 100                      -> clamp to 100
    Returns int (mirrors the prior norm_axis_0_100 bridge). Idempotent.
    """
    if value is None or value == "":
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f <= STORAGE_MAX:
        f = f * 100.0
    if f < PROFILE_MIN:
        f = PROFILE_MIN
    if f > PROFILE_MAX:  # defensive clamp after any future logic change
        f = PROFILE_MAX
    return int(round(f))


def validate_storage_vector(vector):
    """Return True if every numeric axis in `vector` is within 0.0-1.0.

    `vector` is a dict keyed by axis name. Missing axes and None values are
    allowed (not numeric); only present numeric values are range-checked.
    """
    if not isinstance(vector, dict):
        return False
    for ax in CANONICAL_AXES:
        v = vector.get(ax)
        if v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            return False
        if f < STORAGE_MIN or f > STORAGE_MAX:
            return False
    return True


def validate_profile_vector(vector):
    """Return True if every numeric axis in `vector` is within 0-100.

    `vector` is a dict keyed by axis name. Missing axes and None values are
    allowed; only present numeric values are range-checked.
    """
    if not isinstance(vector, dict):
        return False
    for ax in CANONICAL_AXES:
        v = vector.get(ax)
        if v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            return False
        if f < PROFILE_MIN or f > PROFILE_MAX:
            return False
    return True
