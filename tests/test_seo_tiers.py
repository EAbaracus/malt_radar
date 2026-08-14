"""Tier kuralı birim testleri — sentetik veri, production.db'ye bağımlı DEĞİL."""
import sqlite3
from seo.tiers import classify, tier_map

def test_classify_rules():
    assert classify(active_axes=2, has_distillery=True, evidence_count=1) == "A"
    assert classify(active_axes=7, has_distillery=True, evidence_count=5) == "A"
    assert classify(active_axes=2, has_distillery=True, evidence_count=0) == "B"
    assert classify(active_axes=1, has_distillery=True, evidence_count=0) == "B"
    assert classify(active_axes=0, has_distillery=True, evidence_count=0) == "C_idx"
    assert classify(active_axes=0, has_distillery=False, evidence_count=0) == "C_no"

def test_tier_map_full_partition():
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE whiskies (whisky_id TEXT, distillery_id TEXT);
        CREATE TABLE flavor_profiles (whisky_id TEXT, flavor_profile TEXT);
        CREATE TABLE flavor_evidence (whisky_id TEXT);
        INSERT INTO whiskies VALUES ('W1','D1'),('W2','D1'),('W3',NULL),('W4','D1');
        INSERT INTO flavor_profiles VALUES
          ('W1','{"fruity":0.8,"sweet":0.6}'),
          ('W2','{"fruity":0.8,"sweet":0.6}'),
          ('W3','{"fruity":0.8}');
        INSERT INTO flavor_evidence VALUES ('W1');
    """)
    tiers = tier_map(conn)
    assert tiers == {"W1": "A", "W2": "B", "W3": "B", "W4": "C_idx"}
    assert sorted(set(tiers.values())) == ["A", "B", "C_idx"]