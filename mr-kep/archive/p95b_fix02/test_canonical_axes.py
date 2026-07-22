"""P95B-FIX-02 regression tests — all seven canonical axes.

These tests verify the EVIDENCE/CLIENT/REDUCER layers preserve the full canonical
7-axis contract (smoky, peaty, fruity, sweet, spicy, maritime, sherry) WITHOUT
mutating production.db. They import only pure functions / classes.

Run:  python -m pytest mr-kep/p95b_fix02/test_canonical_axes.py -q
"""
from __future__ import annotations
import os, sys, json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "mr-kep", "d4_reducer"))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from flavor_mapper import FlavorMapper  # noqa: E402
from axis_reducer import AxisReducer  # noqa: E402
from ambiguity_handler import AmbiguityHandler  # noqa: E402

# Canonical frozen 7-axis contract (canonical_flavor_standard.md).
CANONICAL_AXES = ["smoky", "peaty", "fruity", "sweet", "spicy", "maritime", "sherry"]


def test_canonical_axes_complete():
    assert set(CANONICAL_AXES) == {"smoky", "peaty", "fruity", "sweet", "spicy", "maritime", "sherry"}
    assert "maritime" in CANONICAL_AXES


def test_flavor_mapper_covers_all_seven_axes():
    fm = FlavorMapper()
    mapped_axes = {fm.get_axis(d) for d in fm.mapping}
    # Every canonical axis must be reachable by at least one descriptor.
    for ax in CANONICAL_AXES:
        assert ax in mapped_axes, f"canonical axis '{ax}' has no descriptor mapping"


def test_flavor_mapper_maritime_descriptors():
    fm = FlavorMapper()
    # P95B-FIX-02: maritime must be present (previously missing).
    for d in ["salt", "brine", "seaweed", "coastal", "sea spray", "marine", "salty"]:
        assert fm.get_axis(d) == "maritime", f"'{d}' should map to maritime"


def test_flavor_mapper_no_rich_canonical():
    fm = FlavorMapper()
    # 'rich' is unmappable -> never canonical.
    assert fm.get_axis("rich") is None
    assert "rich" not in fm.CANONICAL_AXES


def test_axis_reducer_emits_canonical_seven_incl_maritime():
    fm = FlavorMapper()
    ah = AmbiguityHandler()
    reducer = AxisReducer(fm, ah)
    descriptors = [
        {"descriptor": "peat", "intensity": 3, "fact_id": "f1"},
        {"descriptor": "apple", "intensity": 2, "fact_id": "f2"},
        {"descriptor": "seaweed", "intensity": 4, "fact_id": "f3"},  # -> maritime
        {"descriptor": "vanilla", "intensity": 2, "fact_id": "f4"},
        {"descriptor": "rich", "intensity": 3, "fact_id": "f5"},  # unmappable, skipped
    ]
    result, mapped = reducer.reduce_entity_flavor("e1", descriptors)
    vec = result["canonical_vectors"]
    # All 7 canonical axes present as keys.
    assert set(vec.keys()) == set(CANONICAL_AXES)
    # maritime got the seaweed signal.
    assert vec["maritime"] == 4 * 20
    # 'rich' was queued as ambiguous and NOT mapped.
    assert any(q["descriptor"] == "rich" for q in ah.ambiguous_queue)
    assert mapped == 4  # rich excluded


def test_axis_reducer_no_legacy_vocabulary():
    fm = FlavorMapper()
    reducer = AxisReducer(fm, AmbiguityHandler())
    result, _ = reducer.reduce_entity_flavor("e2", [{"descriptor": "peat", "intensity": 1, "fact_id": "x"}])
    vec = result["canonical_vectors"]
    # Legacy stub used Smoke/Medicinal/Fruity/... — must NOT appear.
    assert "Smoke" not in vec and "Medicinal" not in vec and "Woody" not in vec and "Floral" not in vec


def test_db_read_service_exposes_maritime():
    import importlib
    svc = importlib.import_module("app.services.db_read_service")
    # APP_AXES must include maritime (previously dropped).
    assert "maritime" in svc.DbReadService.APP_AXES
    # _normalize_flavor_profile must preserve a stored maritime value.
    raw = json.dumps({"fruity": 5.0, "sweet": 9.0, "spicy": 0.0,
                       "smoky_peaty": 2.0, "oak_cask": 1.0, "malty_cereal": 7.0,
                       "floral_herbal": 0.0, "maritime": 32.0})
    out = json.loads(svc.DbReadService._normalize_flavor_profile(raw))
    assert out.get("maritime") == 32.0, "maritime must survive normalization"
    # All canonical-ish app axes present.
    for ax in svc.DbReadService.APP_AXES:
        assert ax in out, f"app axis '{ax}' missing from normalized output"
