"""P95G — unit tests for the shared flavor scale utilities.

Pure-function tests only: NO production.db / knowledge.db access, NO mutation.
Mirrors the existing mr-kep/p95b_fix02/test_canonical_axes.py style.

Run:  python -m pytest tests/test_flavor_scale_utils.py -q
"""

from __future__ import annotations

import os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "mr-kep", "common"))

from flavor_scale_utils import (  # noqa: E402
    to_storage_scale,
    to_profile_scale,
    validate_storage_vector,
    validate_profile_vector,
    CANONICAL_AXES,
)

STOR = dict(smoky=0.2, peaty=0.1, fruity=0.5, sweet=0.9, spicy=0.3, maritime=0.0, sherry=0.4)
PROF = dict(smoky=20, peaty=10, fruity=50, sweet=90, spicy=30, maritime=0, sherry=40)


# ---- to_storage_scale: individual values ----

def test_storage_none():
    assert to_storage_scale(None) is None

def test_storage_empty_string():
    assert to_storage_scale("") is None

def test_storage_invalid_string():
    assert to_storage_scale("abc") is None

def test_storage_negative_clamped_to_zero():
    assert to_storage_scale(-15) == 0.0

def test_storage_zero():
    assert to_storage_scale(0) == 0.0

def test_storage_half_passthrough():
    assert to_storage_scale(0.5) == 0.5

def test_storage_one_passthrough():
    assert to_storage_scale(1) == 1.0

def test_storage_midscale_divided():
    assert to_storage_scale(50) == 0.5

def test_storage_hundred_divided():
    assert to_storage_scale(100) == 1.0

def test_storage_over_hundred_clamped_to_one():
    assert to_storage_scale(101) == 1.0
    assert to_storage_scale(1000) == 1.0

def test_storage_negative_fifteen_clamped():
    assert to_storage_scale(-15) == 0.0


# ---- to_profile_scale: individual values ----

def test_profile_none():
    assert to_profile_scale(None) is None

def test_profile_empty_string():
    assert to_profile_scale("") is None

def test_profile_invalid_string():
    assert to_profile_scale("abc") is None

def test_profile_zero():
    assert to_profile_scale(0) == 0

def test_profile_half_multiplied():
    assert to_profile_scale(0.5) == 50

def test_profile_one_multiplied():
    assert to_profile_scale(1.0) == 100

def test_profile_midscale_passthrough():
    assert to_profile_scale(50) == 50

def test_profile_hundred_passthrough():
    assert to_profile_scale(100) == 100

def test_profile_over_hundred_clamped():
    assert to_profile_scale(101) == 100
    assert to_profile_scale(1000) == 100

def test_profile_negative_clamped_to_zero():
    assert to_profile_scale(-15) == 0


# ---- roundtrip ----

def test_roundtrip_storage_to_profile():
    # storage 0-1 -> profile 0-100 -> back to storage 0-1
    for v in (0.0, 0.5, 1.0, 0.65):
        assert to_storage_scale(to_profile_scale(v)) == v

def test_roundtrip_profile_to_storage():
    # profile 0-100 -> storage 0-1 -> back to profile 0-100
    for v in (0, 50, 100, 65):
        assert to_profile_scale(to_storage_scale(v)) == v


# ---- cross-layer bridge semantics ----

def test_storage_to_profile_bridge():
    # flavor_evidence (0-1) *100 == canonical_flavor_vectors (0-100)
    assert to_profile_scale(0.65) == 65

def test_profile_to_storage_bridge():
    # canonical 0-100 /100 == storage 0-1
    assert to_storage_scale(65) == 0.65


# ---- idempotency ----

def test_storage_idempotent():
    assert to_storage_scale(to_storage_scale(50)) == to_storage_scale(50) == 0.5
    assert to_storage_scale(to_storage_scale(0.5)) == 0.5

def test_profile_idempotent():
    assert to_profile_scale(to_profile_scale(50)) == to_profile_scale(50) == 50
    assert to_profile_scale(to_profile_scale(0.5)) == 50


# ---- validation ----

def test_validate_storage_vector_ok():
    assert validate_storage_vector(STOR) is True

def test_validate_storage_vector_with_none_ok():
    v = dict(STOR); v["maritime"] = None
    assert validate_storage_vector(v) is True

def test_validate_storage_vector_out_of_range_fails():
    v = dict(STOR); v["smoky"] = 5.0  # > 1.0
    assert validate_storage_vector(v) is False

def test_validate_storage_vector_negative_fails():
    v = dict(STOR); v["sweet"] = -0.1
    assert validate_storage_vector(v) is False

def test_validate_storage_vector_non_dict_fails():
    assert validate_storage_vector("not a dict") is False

def test_validate_profile_vector_ok():
    assert validate_profile_vector(PROF) is True

def test_validate_profile_vector_with_none_ok():
    v = dict(PROF); v["maritime"] = None
    assert validate_profile_vector(v) is True

def test_validate_profile_vector_out_of_range_fails():
    v = dict(PROF); v["smoky"] = 150  # > 100
    assert validate_profile_vector(v) is False

def test_validate_profile_vector_negative_fails():
    v = dict(PROF); v["sweet"] = -5
    assert validate_profile_vector(v) is False

def test_validate_profile_vector_non_dict_fails():
    assert validate_profile_vector(123) is False


# ---- canonical axis contract ----

def test_canonical_axes_seven():
    assert set(CANONICAL_AXES) == {"smoky", "peaty", "fruity", "sweet", "spicy", "maritime", "sherry"}
