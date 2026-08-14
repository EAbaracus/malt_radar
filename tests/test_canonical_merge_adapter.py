"""Unit tests for CanonicalMergeAdapter — synthetic in-memory DB.

No production DB, no files touched. Validates the merge contract:
- remap flavor_evidence / flavor_profiles / price_history
- mark variants duplicate (superseded_by) with NO DELETE
- deterministic plan_hash
- idempotent re-run changes 0 rows
- invalid rows rejected (canon absent / variant==canon)
- merge-specific invariants M1-M9 via verify_canonical_merge
"""

import sqlite3
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_COMMON = str(_ROOT / "mr-kep" / "common")
if _COMMON not in sys.path:
    sys.path.insert(0, _COMMON)

from canonical_merge_adapter import (  # noqa: E402
    CanonicalMergeAdapter,
    verify_canonical_merge,
    MERGE_COLUMN,
)
from domain_adapter import PromotionPlan  # noqa: E402


def _prod_plan(accepted_pairs):
    return PromotionPlan(
        staging_rows=len(accepted_pairs),
        accepted=[
            {"group_name": "grp", "canonical_whisky_id": c, "variant_whisky_id": v}
            for c, v in accepted_pairs
        ],
        rejected=[], skipped=[], duplicate_count=0,
        new_evidence_rows=0, promoted_flavor_profile_rows=0,
    )


def _make_db():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE whiskies (whisky_id TEXT PRIMARY KEY, name TEXT)")
    cur.execute(
        "CREATE TABLE flavor_evidence (evidence_id TEXT PRIMARY KEY, whisky_id TEXT, source TEXT)"
    )
    cur.execute("CREATE TABLE flavor_profiles (whisky_id TEXT, fp TEXT)")
    cur.execute("CREATE TABLE price_history (whisky_id TEXT, price REAL)")
    cur.execute("INSERT INTO whiskies VALUES ('WCANON', 'Base')")
    cur.execute("INSERT INTO whiskies VALUES ('WV1', 'Base Batch 1')")
    cur.execute("INSERT INTO whiskies VALUES ('WV2', 'Base Batch 2')")
    cur.execute("INSERT INTO flavor_evidence VALUES ('E1','WV1','srcA')")
    cur.execute("INSERT INTO flavor_evidence VALUES ('E2','WV2','srcA')")
    cur.execute("INSERT INTO flavor_evidence VALUES ('E3','WV2','srcB')")
    cur.execute("INSERT INTO flavor_profiles VALUES ('WV1','fp1')")
    cur.execute("INSERT INTO flavor_profiles VALUES ('WV2','fp2')")
    cur.execute("INSERT INTO price_history VALUES ('WV1', 50.0)")
    conn.commit()
    return conn


def _make_staging(tmp_path, rows):
    sp = str(tmp_path / "merge_plan.db")
    Path(tmp_path).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(sp)
    conn.execute(
        "CREATE TABLE merge_plan (group_name TEXT, canonical_whisky_id TEXT,"
        " variant_whisky_id TEXT, decision TEXT, PRIMARY KEY (variant_whisky_id))"
    )
    conn.executemany("INSERT INTO merge_plan VALUES (?,?,?,?)", rows)
    conn.commit()
    conn.close()
    return sp


def _make_prod_file(tmp_path):
    """A file-backed production-like DB so plan() validity checks run against it."""
    pp = str(tmp_path / "prod.db")
    Path(tmp_path).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(pp)
    cur = conn.cursor()
    cur.execute("CREATE TABLE whiskies (whisky_id TEXT PRIMARY KEY, name TEXT)")
    cur.execute("INSERT INTO whiskies VALUES ('WCANON', 'Base')")
    cur.execute("INSERT INTO whiskies VALUES ('WV1', 'Base Batch 1')")
    cur.execute("INSERT INTO whiskies VALUES ('WV2', 'Base Batch 2')")
    conn.commit()
    conn.close()
    return pp


def test_plan_rejects_invalid(tmp_path):
    staging = _make_staging(tmp_path, [
        ("grp", "WCANON", "WV1", "SAFE_CANONICALIZE"),
        ("grp", "WCANON", "WV2", "SAFE_CANONICALIZE"),
        ("grp", "WMISSING", "WVX", "SAFE_CANONICALIZE"),  # canon absent
        ("grp", "WCANON", "WCANON", "SAFE_CANONICALIZE"),  # variant == canon
    ])
    prod = _make_prod_file(tmp_path)
    adapter = CanonicalMergeAdapter(staging_db=staging)
    plan = adapter.plan(staging_db=staging, production_db=prod)
    accepted_vids = {a["variant_whisky_id"] for a in plan.accepted}
    rejected_vids = {r["variant_whisky_id"] for r in plan.rejected}
    assert accepted_vids == {"WV1", "WV2"}
    assert rejected_vids == {"WVX", "WCANON"}
    assert plan.new_evidence_rows == 0


def test_apply_plan_remaps_and_marks_no_delete(tmp_path):
    staging = _make_staging(tmp_path, [
        ("grp", "WCANON", "WV1", "SAFE_CANONICALIZE"),
        ("grp", "WCANON", "WV2", "SAFE_CANONICALIZE"),
    ])
    prod = _make_db()
    adapter = CanonicalMergeAdapter(staging_db=staging)
    plan = _prod_plan([("WCANON", "WV1"), ("WCANON", "WV2")])
    result = adapter.apply_plan(plan=plan, staging_db=staging, conn=prod)  # noqa: adapter.plan not needed for apply

    # No DELETE
    assert prod.execute("SELECT COUNT(*) FROM whiskies").fetchone()[0] == 3
    # Variants marked
    marks = prod.execute(
        f"SELECT whisky_id, {MERGE_COLUMN} FROM whiskies WHERE {MERGE_COLUMN} IS NOT NULL"
    ).fetchall()
    assert set(m[0] for m in marks) == {"WV1", "WV2"}
    assert all(m[1] == "WCANON" for m in marks)
    # Evidence remapped
    assert prod.execute("SELECT COUNT(*) FROM flavor_evidence WHERE whisky_id='WCANON'").fetchone()[0] == 3
    assert prod.execute("SELECT COUNT(*) FROM flavor_evidence WHERE whisky_id IN ('WV1','WV2')").fetchone()[0] == 0
    # Profiles remapped
    assert prod.execute("SELECT COUNT(*) FROM flavor_profiles WHERE whisky_id='WCANON'").fetchone()[0] == 2
    # Price remapped
    assert prod.execute("SELECT COUNT(*) FROM price_history WHERE whisky_id='WCANON'").fetchone()[0] == 1
    # result report
    assert result["new_evidence_rows"] == 0
    assert result["remapped_evidence_rows"] == 3
    assert result["marked_duplicates"] == 2
    assert result["merged_variant_ids"] == ["WV1", "WV2"]

    v = verify_canonical_merge(prod, ["WV1", "WV2"], pre_whisky_count=3, pre_evidence_count=3)
    assert v["all_passed"], v


def test_idempotent_rerun_changes_zero(tmp_path):
    staging = _make_staging(tmp_path, [
        ("grp", "WCANON", "WV1", "SAFE_CANONICALIZE"),
        ("grp", "WCANON", "WV2", "SAFE_CANONICALIZE"),
    ])
    prod = _make_db()
    adapter = CanonicalMergeAdapter(staging_db=staging)
    plan = _prod_plan([("WCANON", "WV1"), ("WCANON", "WV2")])
    adapter.apply_plan(plan, staging_db=staging, conn=prod)
    r2 = adapter.apply_plan(plan, staging_db=staging, conn=prod)
    assert r2["marked_duplicates"] == 2
    assert r2["remapped_evidence_rows"] == 0


def test_deterministic_plan_hash(tmp_path):
    rows = [
        ("grp", "WCANON", "WV1", "SAFE_CANONICALIZE"),
        ("grp", "WCANON", "WV2", "SAFE_CANONICALIZE"),
    ]
    s1 = _make_staging(tmp_path / "a", rows)
    s2 = _make_staging(tmp_path / "b", rows)
    prod = _make_prod_file(tmp_path / "a")
    a1 = CanonicalMergeAdapter(staging_db=s1)
    a2 = CanonicalMergeAdapter(staging_db=s2)
    p1 = a1.plan(staging_db=s1, production_db=prod)
    p2 = a2.plan(staging_db=s2, production_db=prod)
    assert p1.plan_hash == p2.plan_hash


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
