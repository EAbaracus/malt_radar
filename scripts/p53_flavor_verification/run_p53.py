# =============================================================================
# P53 - Repeatable Verification Pipeline (orchestrator, READ-ONLY)
# Phases:
#   P1  integrity baseline (keyed logical snapshot of production.db)
#   P2  verification engine (temp db copy -> P53 ledger)
#   P3  report generator (9 deliverables)
#   P4  integrity verify (live DB logically unchanged)
#   P5  run manifest
# =============================================================================
import os
import sys
import json
import sqlite3
import shutil
import tempfile
import subprocess
import hashlib
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config.source_authority_matrix as M
import verification_engine as V
import report_generator as R

REPO = r"C:\Users\eltun\Documents\malt radar CLEAN"
BASELINE = os.path.join(M.OUT_DIR, "integrity_baseline.json")


def _keyed_snapshot(db_path):
    """Logical (keyed) snapshot -> order-independent content hash per table.
    Authoritative proof that no row was added/changed/deleted.
    Opens READ-ONLY (mode=ro) so the live DB is never checkpointed/modified."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.text_factory = str
    cur = con.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [r[0] for r in cur.fetchall()]
    snap = {}
    for t in tables:
        cur.execute(f"SELECT * FROM '{t}'")
        rows = cur.fetchall()
        # hash the MULTISET of rows: each row individually, then sort the
        # per-row digests so physical order / WAL checkpoint reordering is
        # irrelevant. This is a true content-equality proof.
        row_hashes = sorted(hashlib.sha256(
            json.dumps(row, default=str, sort_keys=True).encode("utf-8")).hexdigest()
            for row in rows)
        agg = hashlib.sha256(("".join(row_hashes)).encode("utf-8")).hexdigest()
        snap[t] = (len(rows), agg[:16])
    con.close()
    return snap


def phase1_baseline():
    os.makedirs(M.OUT_DIR, exist_ok=True)
    snap = _keyed_snapshot(M.LIVE_DB)
    with open(BASELINE, "w", encoding="utf-8") as f:
        json.dump({"run": datetime.now(timezone.utc).isoformat(),
                   "live_db_bytes": os.path.getsize(M.LIVE_DB),
                   "snapshot": snap}, f, indent=2)
    print(f"[P1] integrity baseline captured ({len(snap)} tables)")


def phase4_verify():
    base = json.load(open(BASELINE, encoding="utf-8"))["snapshot"]
    cur = _keyed_snapshot(M.LIVE_DB)
    # baseline stores (rows, hash) as a JSON list; compare by VALUE (hash + rowcount),
    # not by tuple/list identity, to avoid false "changed" on list-vs-tuple.
    diff = [t for t in base
            if (base[t][0], base[t][1]) != (cur.get(t, (0, ""))[0], cur.get(t, (0, ""))[1])]
    if diff:
        print(f"[P4] RESULT: production.db LOGICALLY CHANGED in tables: {diff}")
        return False
    print("[P4] RESULT: production.db LOGICALLY UNCHANGED (data not modified).")
    return True


def main():
    print("=" * 64)
    print("P53 FLAVOR & TASTING VERIFICATION PIPELINE (READ-ONLY)")
    print("=" * 64)
    print("\n[P1] integrity snapshot baseline")
    phase1_baseline()
    print("\n[P2] verification engine")
    led, conf, man, low, tnc, miss, disag, bf, imp = V.verify()
    print(f"     ledger={len(led)} conflicts={len(conf)} manual={len(man)} "
          f"lowconf={len(low)} tnflags={len(tnc)} missing={len(miss)} "
          f"batch={len(bf)} disag={len(disag)} impact%={imp['pct_changed']}")
    print("\n[P3] report generator")
    R.generate(led, conf, man, low, tnc, miss, disag, bf, imp)
    print("\n[P4] integrity verify (logical)")
    ok = phase4_verify()
    print("\n[P5] run manifest")
    manifest = {
        "run": datetime.now(timezone.utc).isoformat(),
        "live_db": M.LIVE_DB,
        "live_db_bytes": os.path.getsize(M.LIVE_DB),
        "live_db_sha256_byte": hashlib.sha256(
            open(M.LIVE_DB, "rb").read()).hexdigest(),
        "report_dir": M.OUT_DIR,
        "counts": {
            "ledger_rows": len(led), "conflicts": len(conf), "manual": len(man),
            "low_confidence": len(low), "tasting_flags": len(tnc),
            "missing": len(miss), "batch_divergences": len(bf),
            "disagreements": len(disag),
            "impact_pct_changed": imp["pct_changed"],
        },
        "logical_integrity_ok": ok,
        "note": "Byte-level SHA may differ from baseline due to SQLite WAL "
                "checkpoint on open; logical keyed snapshot is the authoritative gate.",
    }
    with open(os.path.join(M.OUT_DIR, "run_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print("manifest ->", os.path.join(M.OUT_DIR, "run_manifest.json"))
    if not ok:
        sys.exit(2)


if __name__ == "__main__":
    main()
