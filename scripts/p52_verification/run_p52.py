# =============================================================================
# P52 - Repeatable Verification Pipeline (orchestrator)
# -----------------------------------------------------------------------------
# Single entry point. Deterministic, read-only, reproducible.
#
# Phases:
#   P1  snapshot integrity baseline (logical, keyed)
#   P2  run verification engine  -> reports/p52/verification_ledger.csv
#   P3  run report generator     -> 8 report files
#   P4  verify integrity         -> production.db logically unchanged
#   P5  write run manifest (config + counts + live-db byte hash for transparency)
#
# The live production.db is NEVER opened by the engine/reports; they read a
# private temp copy. The orchestrator opens the live file ONLY for a one-way
# byte-hash snapshot (read) used purely as a transparent record; the
# authoritative "not modified" proof is the KEYED LOGICAL baseline (Phase P4).
# =============================================================================

import os
import sys
import json
import hashlib
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from config import source_authority_matrix as M   # noqa: E402

STEPS = ["verification_engine.py", "report_generator.py", "integrity_check.py"]


def run():
    print("=" * 64)
    print("P52 METADATA VERIFICATION PIPELINE (READ-ONLY)")
    print("=" * 64)
    # P1 baseline
    print("\n[P1] integrity snapshot baseline")
    subprocess.run([sys.executable, os.path.join(HERE, "integrity_check.py"),
                    "snapshot"], check=True)
    # P2 engine
    print("\n[P2] verification engine")
    subprocess.run([sys.executable, os.path.join(HERE, "verification_engine.py")],
                   check=True)
    # P3 reports
    print("\n[P3] report generator")
    subprocess.run([sys.executable, os.path.join(HERE, "report_generator.py")],
                   check=True)
    # P4 integrity verify
    print("\n[P4] integrity verify (logical)")
    subprocess.run([sys.executable, os.path.join(HERE, "integrity_check.py"),
                    "verify"], check=True)
    # P5 manifest
    print("\n[P5] run manifest")
    _manifest()


def _manifest():
    # byte hash of live db for transparency only (WAL byte flux is expected)
    byte_hash = hashlib.sha256(open(M.LIVE_DB, "rb").read()).hexdigest()
    ledger = os.path.join(M.OUTPUT_DIR, "verification_ledger.csv")
    rows = sum(1 for _ in open(ledger, encoding="utf-8")) - 1 if os.path.exists(ledger) else 0
    mani = {
        "schema_version": M.SCHEMA_VERSION,
        "run_date": M.RUN_DATE,
        "live_db": M.LIVE_DB,
        "live_db_byte_sha256": byte_hash,
        "live_db_byte_hash_note": "WAL-mode file: byte hash fluctuates on open; "
                                  "authoritative integrity = keyed logical baseline "
                                  "(reports/p52/integrity_baseline.json).",
        "ledger_rows": rows,
        "outputs": [
            "verification_ledger.csv", "verification_summary.md",
            "source_authority_matrix.md", "confidence_statistics.md",
            "field_coverage.md", "conflicts.csv", "missing_metadata.csv",
            "manual_review_queue.csv", "source_disagreements.csv",
            "integrity_baseline.json",
        ],
        "reproducible": True,
        "production_data_modified": False,
    }
    p = os.path.join(M.OUTPUT_DIR, "run_manifest.json")
    json.dump(mani, open(p, "w"), indent=2)
    print(f"manifest -> {p}")


if __name__ == "__main__":
    run()
