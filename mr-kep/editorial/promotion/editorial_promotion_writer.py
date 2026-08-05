"""P96A — Editorial Promotion foundation (IMPLEMENTATION GO / EXECUTION NO-GO).

Bridges editorial staging -> production flavor pipeline WITHOUT changing the
flavor scale contract (P95C/P95D/P95G frozen). Reads staging_editorial.db,
validates rows, and prepares flavor_evidence inserts (0-1) via shared
flavor_scale_utils. The pipeline's downstream consensus (P136 ingest.py)
bridges flavor_evidence (0-1) -> canonical_flavor_vectors (0-100) unchanged.

Promotion is NEVER executed by this module on its own. Default mode is --dry-run.
Only an explicit --execute (plus human GO per DB-safety rules) performs writes,
and even then it takes a backup + SHA256 + atomic transaction with rollback.

No production.db write occurs unless --execute is passed AND a transaction
commits. Dry-run opens production.db read-only and reports the plan only.

FIXED-AXES (P96A-2): flavor_profiles.flavor_profile is written with the app
presentation axes (0-100) per the Dart normalizer contract. Storage axes
(smoky/peaty/maritime/sherry) are preserved in flavor_evidence only.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import shutil
import sqlite3
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "mr-kep", "common"))
from flavor_scale_utils import (  # noqa: E402
    to_storage_scale,
    to_profile_scale,
    validate_storage_vector,
    validate_profile_vector,
    CANONICAL_AXES,
)

# flavor_evidence stores 7 canonical axes + non-canonical 'vector_rich' (legacy col).
EVIDENCE_AXES = CANONICAL_AXES  # smoky, peaty, fruity, sweet, spicy, maritime, sherry
# flavor_profiles presentation axes — app contract (Dart normalizer).
# NOT exported by flavor_scale_utils; defined locally to keep scale utils untouched.
PROFILE_AXES = ["fruity", "sweet", "spicy", "smoky_peaty", "oak_cask", "malty_cereal", "floral_herbal"]
EVIDENCE_INSERT_COLS = (
    "evidence_id, whisky_id, source, vector_smoky, vector_peaty, "
    "vector_fruity, vector_sweet, vector_spicy, vector_maritime, vector_sherry, vector_rich"
)
# match_status values accepted for promotion (everything else needs human review).
PROMOTABLE_MATCH = {"exact", "normalized_exact", "fuzzy"}
# provenance_state values rejected outright.
REJECTED_PROVENANCE = {"staging_rejected", "rejected", "quality_rejected"}

STAGING_DB = os.path.join(ROOT, "mr-kep", "editorial", "staging_editorial.db")
PROD_DB = os.path.join(ROOT, "output", "import", "production.db")
BACKUP_DIR = os.path.join(ROOT, "mr-kep", "editorial", "promotion", "backups")


class PromotionError(Exception):
    """Raised for a hard promotion failure (bad config / IO / schema)."""


class RowRejected(Exception):
    """A single row failed validation; carries a reason for reporting."""

    def __init__(self, evidence_id, reason):
        super().__init__(reason)
        self.evidence_id = evidence_id
        self.reason = reason


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(65536), b""):
            h.update(blk)
    return h.hexdigest()


def _parse_vector(raw_json):
    """Parse flavor_vector_json into a dict; raise ValueError on bad JSON."""
    if not raw_json:
        raise ValueError("empty flavor_vector_json")
    return json.loads(raw_json)


def validate_staging_row(row: dict):
    """Validate one staging row. Returns (whisky_id, evidence_id, storage_vec, profile_vec).

    Raises RowRejected(reason) on any gate failure. Mirrors P95D/P95G quality gates:
    duplicate evidence, invalid whisky_id, invalid provenance, non-canonical axes,
    invalid storage scale.
    """
    eid = row["evidence_id"]
    wid = row["matched_master_whisky_id"]
    if not wid:
        raise RowRejected(eid, "invalid whisky_id: matched_master_whisky_id is NULL")
    if row["match_status"] not in PROMOTABLE_MATCH:
        raise RowRejected(eid, f"non-promotable match_status={row['match_status']!r} (needs human review)")
    prov = (row.get("provenance_state") or "").lower()
    if any(r in prov for r in REJECTED_PROVENANCE):
        raise RowRejected(eid, f"invalid provenance_state={row['provenance_state']!r}")

    try:
        vec = _parse_vector(row["flavor_vector_json"])
    except Exception as e:
        raise RowRejected(eid, f"malformed flavor_vector_json: {e}")
    # canonical-axis check: reject non-canonical axes, require all 7 present
    for ax in EVIDENCE_AXES:
        if ax not in vec:
            raise RowRejected(eid, f"missing canonical axis {ax!r}")
    extra = set(vec.keys()) - set(EVIDENCE_AXES)
    if extra:
        raise RowRejected(eid, f"non-canonical axes present: {sorted(extra)}")
    # storage scale check (0-1). validate_storage_vector tolerates None; we require present numerics.
    if not validate_storage_vector(vec):
        raise RowRejected(eid, "invalid storage scale (axis outside 0-1)")

    # convert to storage scale (idempotent on already-0-1 staging vectors)
    storage_vec = {ax: to_storage_scale(vec[ax]) for ax in EVIDENCE_AXES}
    # Presentation profile: map storage axes -> app presentation axes (0-100).
    # maritime/sherry have no presentation counterpart -> dropped from the
    # profile JSON (fully preserved in flavor_evidence storage vector).
    # oak_cask/malty_cereal/floral_herbal -> 0 (never fabricated).
    # None storage values -> 0 (presentation JSON stays fully numeric;
    # Dart normalizer treats null as 0 anyway, this keeps it explicit).
    profile_vec = {
        "fruity": to_profile_scale(vec["fruity"]) or 0.0,
        "sweet": to_profile_scale(vec["sweet"]) or 0.0,
        "spicy": to_profile_scale(vec["spicy"]) or 0.0,
        "smoky_peaty": to_profile_scale(max(vec["smoky"] or 0.0, vec["peaty"] or 0.0)),
        "oak_cask": 0.0,
        "malty_cereal": 0.0,
        "floral_herbal": 0.0,
    }
    # local range check: every presentation axis must be numeric in [0, 100]
    if not all(isinstance(v, (int, float)) and 0.0 <= v <= 100.0 for v in profile_vec.values()):
        raise RowRejected(eid, "invalid profile vector (presentation axes must be 0-100)")
    return wid, eid, storage_vec, profile_vec


class EditorialPromotionWriter:
    """Reads staging, validates, and prepares flavor_evidence (and flavor_profiles) inserts.

    Does NOT open production.db for writing. `plan()` returns a structured result
    the transaction wrapper executes (or reports in dry-run).
    """

    def __init__(self, staging_db: str = STAGING_DB, prod_db: str = PROD_DB):
        self.staging_db = staging_db
        self.prod_db = prod_db

    def plan(self):
        """Compute the promotion plan. Read-only against both DBs.

        Returns dict with: rows (prepared inserts), accepted, rejected, skipped,
        duplicate_count, plus summary stats (axis coverage, confidence distribution).
        """
        if not os.path.exists(self.staging_db):
            raise PromotionError(f"staging db missing: {self.staging_db}")
        st = sqlite3.connect(self.staging_db)
        st.row_factory = sqlite3.Row
        rows = st.execute("SELECT * FROM staging_editorial_reviews").fetchall()
        st.close()

        # read-only check of existing production state (whisky keys + existing evidence ids)
        prod = sqlite3.connect(f"file:{self.prod_db}?mode=ro", uri=True)
        prod.row_factory = sqlite3.Row
        valid_wids = {r[0] for r in prod.execute("SELECT whisky_id FROM whiskies")}
        existing_ev = {r[0] for r in prod.execute("SELECT evidence_id FROM flavor_evidence")}
        existing_fp = {r[0] for r in prod.execute("SELECT whisky_id FROM flavor_profiles")}
        prod.close()

        prepared = []
        accepted, rejected, skipped, duplicates = [], [], [], []
        fp_written: set = set()  # intra-batch dedup: one canonical profile per whisky_id
        axis_present = {ax: 0 for ax in EVIDENCE_AXES}
        conf_bins = {"<0.7": 0, "0.7-0.85": 0, "0.85-0.95": 0, ">=0.95": 0}

        for r in rows:
            row = dict(r)
            eid = row["evidence_id"]
            # duplicate evidence (already promoted)
            if eid in existing_ev:
                duplicates.append(eid)
                skipped.append({"evidence_id": eid, "reason": "duplicate evidence_id already in flavor_evidence"})
                continue
            # whisky_id existence
            if row["matched_master_whisky_id"] not in valid_wids:
                rejected.append({"evidence_id": eid, "reason": "invalid whisky_id (not in production.whiskies)"})
                continue
            try:
                wid, _eid, svec, pvec = validate_staging_row(row)
            except RowRejected as ex:
                rejected.append({"evidence_id": ex.evidence_id, "reason": ex.reason})
                continue

            ev_tuple = (
                eid, wid, row.get("source_id") or "editorial",
                svec["smoky"], svec["peaty"], svec["fruity"], svec["sweet"],
                svec["spicy"], svec["maritime"], svec["sherry"], None,  # vector_rich legacy col -> None
            )
            # One canonical flavor_profile per whisky_id per batch: the FIRST
            # row for a whisky_id writes the profile; later rows (other sources)
            # add flavor_evidence only. Deterministic: row order is the staging
            # INSERT order (evidence_id order).
            wants_fp = wid not in existing_fp and wid not in fp_written
            fp_written.add(wid)
            fp_tuple = (wid, json.dumps({ax: pvec[ax] for ax in PROFILE_AXES})) if wants_fp else None
            prepared.append({
                "evidence_id": eid,
                "whisky_id": wid,
                "match_status": row["match_status"],
                "evidence_confidence": row["evidence_confidence"],
                "flavor_evidence": ev_tuple,
                "flavor_profiles": fp_tuple,
            })
            accepted.append(eid)
            for ax in EVIDENCE_AXES:
                if svec[ax] is not None and svec[ax] > 0:
                    axis_present[ax] += 1
            ec = row.get("evidence_confidence") or 0.0
            if ec < 0.7: conf_bins["<0.7"] += 1
            elif ec < 0.85: conf_bins["0.7-0.85"] += 1
            elif ec < 0.95: conf_bins["0.85-0.95"] += 1
            else: conf_bins[">=0.95"] += 1

        return {
            "staging_rows": len(rows),
            "prepared": prepared,
            "accepted": accepted,
            "rejected": rejected,
            "skipped": skipped,
            "duplicate_count": len(duplicates),
            "axis_coverage": axis_present,
            "confidence_distribution": conf_bins,
            "new_evidence_rows": len(prepared),
            "promoted_flavor_profile_rows": sum(1 for p in prepared if p["flavor_profiles"] is not None),
        }

    def execute(self, plan_result=None, backup=True):
        """EXECUTES the promotion against production.db. GATED: backup + SHA256 + atomic txn.

        Returns dict with sha256_before/after and counts. Raises PromotionError on
        any failure after rolling back (DB transaction + backup restore).
        """
        if plan_result is None:
            plan_result = self.plan()
        if not plan_result["prepared"]:
            return {"executed": False, "reason": "nothing to promote", "new_evidence_rows": 0}

        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = os.path.join(BACKUP_DIR, f"production.pre_editorial_promo.{ts}.db")
        sha_before = sha256_file(self.prod_db)
        if backup:
            shutil.copy2(self.prod_db, bak)

        conn = sqlite3.connect(self.prod_db)
        try:
            cur = conn.cursor()
            new_ev = 0
            new_fp = 0
            for p in plan_result["prepared"]:
                cur.execute(
                    f"INSERT INTO flavor_evidence ({EVIDENCE_INSERT_COLS}) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    p["flavor_evidence"],
                )
                new_ev += 1
                if p["flavor_profiles"] is not None:
                    cur.execute(
                        "INSERT INTO flavor_profiles (whisky_id, flavor_profile) VALUES (?,?)",
                        p["flavor_profiles"],
                    )
                    new_fp += 1
            # R4 hard gate: abort if any flavor_evidence axis exceeds 1.0
            bad = cur.execute(
                "SELECT COUNT(*) FROM flavor_evidence WHERE "
                "vector_smoky>1.0 OR vector_peaty>1.0 OR vector_sherry>1.0 OR vector_fruity>1.0 "
                "OR vector_sweet>1.0 OR vector_spicy>1.0 OR vector_maritime>1.0"
            ).fetchone()[0]
            if bad:
                raise PromotionError(f"R4 invariant violated: {bad} rows with axis>1.0")
            conn.commit()
        except Exception as e:
            conn.rollback()
            if backup and os.path.exists(bak):
                shutil.copy2(bak, self.prod_db)  # restore pre-promotion state
            raise PromotionError(f"promotion aborted, rolled back + restored backup: {e}")
        finally:
            conn.close()

        return {
            "executed": True,
            "backup": bak,
            "sha256_before": sha_before,
            "sha256_after": sha256_file(self.prod_db),
            "new_evidence_rows": new_ev,
            "new_flavor_profile_rows": new_fp,
        }


def main(argv=None):
    ap = argparse.ArgumentParser(description="P96A editorial promotion writer")
    ap.add_argument("--staging-db", default=STAGING_DB)
    ap.add_argument("--prod-db", default=PROD_DB)
    ap.add_argument("--execute", action="store_true", help="perform write (default: dry-run)")
    args = ap.parse_args(argv)

    writer = EditorialPromotionWriter(args.staging_db, args.prod_db)
    plan = writer.plan()
    print(f"[dry-run] staging_rows={plan['staging_rows']} accepted={len(plan['accepted'])} "
          f"rejected={len(plan['rejected'])} skipped={len(plan['skipped'])} "
          f"duplicates={plan['duplicate_count']}")
    print(f"[dry-run] new flavor_evidence rows planned={plan['new_evidence_rows']} "
          f"new flavor_profiles rows planned={plan['promoted_flavor_profile_rows']}")
    print(f"[dry-run] axis_coverage={plan['axis_coverage']}")
    print(f"[dry-run] confidence_distribution={plan['confidence_distribution']}")
    for r in plan["rejected"]:
        print(f"[rejected] {r['evidence_id']}: {r['reason']}")

    if args.execute:
        print("[EXECUTE] running gated promotion...")
        res = writer.execute(plan, backup=True)
        print(f"[EXECUTE] done: {res}")
    else:
        print("[dry-run] no writes performed (pass --execute to promote).")
    return plan


if __name__ == "__main__":
    main()
