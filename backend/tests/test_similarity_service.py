import contextlib
import json
import sqlite3

import pytest

from app.services.similarity_service import SimilarityService


@pytest.fixture
def service():
    return SimilarityService()


# ---------------------------------------------------------------------------
# Hermetic in-memory fake (edge-case tests) — no production.db dependency
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE whiskies (
    whisky_id TEXT PRIMARY KEY,
    name TEXT,
    superseded_by TEXT,
    brand TEXT,
    region TEXT,
    type TEXT,
    country TEXT,
    meta_critic_score REAL,
    user_score REAL,
    original_name TEXT,
    distillery_id TEXT
);
CREATE TABLE distilleries (
    distillery_id TEXT,
    name TEXT
);
CREATE TABLE flavor_profiles (
    whisky_id TEXT,
    flavor_profile TEXT
);
"""


class _FakeAdapter:
    """In-memory stand-in for ProductionReadAdapter (hermetic edge tests).

    ``raw_connection()`` must mirror the real seam: the production adapter
    returns a read-only connection with ``row_factory = sqlite3.Row``, which
    the service relies on to ``dict(r)`` each row. We set the same row_factory
    here and wrap the connection in a nullcontext so it is reusable across
    ``with self._adapter.raw_connection() as conn:`` blocks.
    """

    def __init__(self, conn: sqlite3.Connection):
        conn.row_factory = sqlite3.Row
        self._conn = conn

    def raw_connection(self):
        return contextlib.nullcontext(self._conn)


def _build_service(whiskies, profiles):
    """Create an in-memory SimilarityService seeded with the given rows.

    ``whiskies``: list of 11-tuples matching the whiskies columns above
        (whisky_id, name, superseded_by, brand, region, type, country,
         meta_critic_score, user_score, original_name, distillery_id).
    ``profiles``: list of (whisky_id, flavor_profile JSON string) tuples.
    """
    conn = sqlite3.connect(":memory:")
    conn.executescript(_SCHEMA)
    conn.executemany(
        "INSERT INTO whiskies (whisky_id, name, superseded_by, brand, region, "
        "type, country, meta_critic_score, user_score, original_name, "
        "distillery_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        whiskies,
    )
    conn.executemany(
        "INSERT INTO flavor_profiles (whisky_id, flavor_profile) VALUES (?,?)",
        profiles,
    )
    conn.commit()
    return SimilarityService(adapter=_FakeAdapter(conn))


# App-axis JSON profiles (already in the 7-axis vocabulary, so the backend
# normalize pass leaves them intact).
_PROFILE_A = (
    '{"fruity": 6, "sweet": 4, "spicy": 3, "smoky_peaty": 1, '
    '"oak_cask": 5, "malty_cereal": 4, "floral_herbal": 2}'
)
_PROFILE_B = (
    '{"fruity": 1, "sweet": 1, "spicy": 1, "smoky_peaty": 9, '
    '"oak_cask": 1, "malty_cereal": 1, "floral_herbal": 1}'
)


# ---------------------------------------------------------------------------
# Existing production tests (unchanged)
# ---------------------------------------------------------------------------

def test_unknown_target_returns_none(service):
    assert service.get_similar("DOES-NOT-EXIST-999", limit=5) is None


def test_self_excluded_and_ordered(service):
    ids = service._candidate_profiles()
    assert len(ids) > 100, "full-pool bekleniyor, bounded havuz değil"
    target = next(iter(ids))
    result = service.get_similar(target, limit=5)
    assert result, "en az 1 benzer olmalı"
    assert len(result) <= 5
    assert all(r["whisky_id"] != target for r in result)
    distances = [r["distance"] for r in result]
    assert distances == sorted(distances)
    assert all(0.0 <= r["similarity"] <= 1.0 for r in result)


def test_full_pool_not_alphabetical_first_250(service):
    rows = service._all_active_whiskies()
    name_ordered = sorted(rows, key=lambda r: (r.get("name") or "").lower())
    first250 = {r["whisky_id"] for r in name_ordered[:250]}
    target = next(iter(service._candidate_profiles()))
    result = service.get_similar(target, limit=5)
    assert any(r["whisky_id"] not in first250 for r in result), \
        "benzerlik yalnızca alfabetik ilk 250 havuzundan geldi (bug)"


def test_no_profile_target_returns_empty(service):
    rows = service._all_active_whiskies()
    no_profile = [r for r in rows if not r.get("flavor_profile")]
    if no_profile:
        assert service.get_similar(no_profile[0]["whisky_id"], limit=5) == []


# ---------------------------------------------------------------------------
# New hermetic edge-case tests
# ---------------------------------------------------------------------------

def _make_profile(sweet: int) -> str:
    """Build a distinct 7-axis app-profile JSON with a unique ``sweet`` value."""
    return json.dumps({
        "fruity": 5,
        "sweet": sweet,
        "spicy": 3,
        "smoky_peaty": 2,
        "oak_cask": 4,
        "malty_cereal": 3,
        "floral_herbal": 2,
    })


def test_limit_clamped():
    # Hermetic pool: 1 target (W-T) + 25 candidates (W-01..W-25), every whisky
    # on a distinct 7-axis profile so all 25 non-self candidates are present.
    # Exact-count asserts make each branch fail if the clamp in get_similar()
    # is removed:
    #   limit=0  -> clamp->1  (no clamp: scored[:0]  == 0  items -> FAIL)
    #   limit=-5 -> clamp->1  (no clamp: scored[:-5] == 20 items -> FAIL)
    #   limit=50 -> clamp->20 (no clamp: scored[:50] == 25 items -> FAIL)
    whisky_ids = ["W-T"] + [f"W-{i:02d}" for i in range(1, 26)]
    whiskies = [
        (wid, f"Whisky {wid}", None, "BrandX", "Speyside", "Single Malt",
         "Scotland", 90.0, 88.0, None, None)
        for wid in whisky_ids
    ]
    profiles = [
        (wid, _make_profile(sweet)) for sweet, wid in enumerate(whisky_ids, start=1)
    ]
    svc = _build_service(whiskies, profiles)

    # Pool sanity: 26 profiled whiskies -> 25 non-self candidates available
    # (verified against the raw profile pool, independent of the clamp).
    pool = svc._candidate_profiles()
    assert len(pool) == 26
    assert "W-T" in pool

    # limit=0 -> clamped to 1.
    assert len(svc.get_similar("W-T", limit=0)) == 1
    # limit=-5 -> clamped to 1.
    assert len(svc.get_similar("W-T", limit=-5)) == 1
    # limit=50 -> clamped to 20.
    assert len(svc.get_similar("W-T", limit=50)) == 20


def test_twin_profiles_similarity_1():
    whiskies = [
        ("w1", "Twin One", None, "BrandA", "Speyside", "Single Malt",
         "Scotland", 90.0, 88.0, None, None),
        ("w2", "Twin Two", None, "BrandA", "Speyside", "Single Malt",
         "Scotland", 91.0, 89.0, None, None),
        ("w3", "Different", None, "BrandB", "Islay", "Single Malt",
         "Scotland", 88.0, 85.0, None, None),
    ]
    profiles = [("w1", _PROFILE_A), ("w2", _PROFILE_A), ("w3", _PROFILE_B)]
    svc = _build_service(whiskies, profiles)

    for target, twin in (("w1", "w2"), ("w2", "w1")):
        result = svc.get_similar(target, limit=5)
        assert result, "en az 1 aday olmalı"
        top = result[0]
        assert top["whisky_id"] == twin
        assert top["similarity"] == 1.0
        assert top["distance"] == 0.0
        # The different-profile whisky must sort last (largest distance).
        assert result[-1]["whisky_id"] == "w3"
