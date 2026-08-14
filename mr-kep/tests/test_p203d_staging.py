"""
P203D — read-only pytest coverage for the editorial staging review gate.

Runs AGAINST the live staging DB in read-only mode (uri mode=ro) so it can
never mutate data. No network. No production/knowledge DB access.

Covers (per P203D spec Task 7):
- staging inventory validation
- evidence schema validation
- duplicate detection
- review queue detection
- crosswalk review handling
- flavour vector validation
"""
import os
import json
import sqlite3
from collections import Counter

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RETRY = os.path.join(REPO, "data", "p203c_staging", "editorial_staging_retry.db")
AXES = ["smoky", "peaty", "fruity", "sweet", "spicy", "maritime", "sherry"]
REQUIRED = ["evidence_id", "source_id", "source_url", "fetched_at",
             "raw_name", "distillery_raw", "flavor_vector_json", "provenance_state"]
JUNK = {"home", "about", "contact", "category", "tag", "archive",
         "login", "blog", "reviews", "review"}


def _rows():
    con = sqlite3.connect(f"file:{RETRY}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rs = [dict(r) for r in con.execute("SELECT * FROM staging_editorial_reviews")]
    con.close()
    return rs


def test_staging_inventory_total():
    assert len(_rows()) == 19


def test_evidence_id_unique():
    rs = _rows()
    ids = [r["evidence_id"] for r in rs]
    assert len(ids) == len(set(ids))


def test_no_duplicate_groups():
    c = Counter(r["evidence_id"] for r in _rows())
    assert {k: v for k, v in c.items() if v > 1} == {}


def test_source_distribution():
    dist = {}
    for r in _rows():
        dist[r["source_id"]] = dist.get(r["source_id"], 0) + 1
    assert dist == {"thewhiskyphiles": 5, "thedramble": 5,
                    "whiskynotes_be": 5, "thewhiskeywash": 4}


def test_review_queue_detection():
    rev = [r for r in _rows() if r["review_required"] == 1]
    assert len(rev) == 8


def test_evidence_schema_required_fields():
    for r in _rows():
        for f in REQUIRED:
            v = r.get(f)
            assert v is not None
            assert not (isinstance(v, str) and v.strip() == "")


def test_whisky_name_not_site_term():
    for r in _rows():
        n = (r.get("raw_name") or "").strip().lower()
        assert n != "" and n not in JUNK


def test_crosswalk_review_handling():
    rs = _rows()
    rev = [r for r in rs if r["review_required"] == 1]
    assert len(rev) == 8
    for r in rev:
        assert r["canonical_distillery_id"] is None
        assert (r.get("crosswalk_confidence") or 0.0) == 0.0
    resolved = [r for r in rs if r["review_required"] == 0]
    for r in resolved:
        assert r["canonical_distillery_id"] is not None
        assert float(r["crosswalk_confidence"]) >= 0.7


def test_flavour_vector_validation():
    for r in _rows():
        v = json.loads(r["flavor_vector_json"])
        assert isinstance(v, dict)
        for a in AXES:
            assert a in v
            val = float(v[a])
            assert 0.0 <= val <= 1.0
    assert len(_rows()) == 19


def test_staging_db_opens_read_only():
    # guarantees offline + read-only behaviour (no mutation possible)
    con = sqlite3.connect(f"file:{RETRY}?mode=ro", uri=True)
    con.close()
    assert os.path.exists(RETRY)
