"""PromotionGate PREPARE + DRY-RUN only (read-only w.r.t. production).

Per AGENTS.md rule 6/8: dry-run output MUST be presented to the human and
explicit GO obtained before any apply. This script NEVER calls apply();
it stops after dry-run and prints the report for the human gate.

Usage:
    python kep_review_runtime/runtime/run_dryrun_editorial.py \
        --staging output/staging/unified_staging.db
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # repo root
sys.path.insert(0, str(ROOT / "kep_review_runtime"))
sys.path.insert(0, str(ROOT))

from runtime.promotion_engine import PromotionEngine  # noqa: E402
from runtime.promotion_engine import PromotionGate  # noqa: E402
from runtime.audit_writer import AuditWriter  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--staging", default=str(ROOT / "output/staging/unified_staging.db"))
    ap.add_argument("--production", default=str(ROOT / "output/import/production.db"))
    ap.add_argument("--phase", default="P501-EDITORIAL")
    args = ap.parse_args()

    audit = AuditWriter(str(ROOT / "kep_review_runtime" / "runtime" / "runtime.db"))
    engine = PromotionEngine(args.staging, args.production, adapter_name="editorial",
                             audit_writer=audit)
    gate = PromotionGate(engine, args.staging, args.production)

    print(f"=== PREPARE ({args.phase}) ===")
    prep = gate.prepare(args.phase)
    print(f"  staging rows      : {prep.staging_row_count}")
    print(f"  expected inserts  : {prep.expected_inserts}")
    print(f"  expected skips    : {prep.expected_skips}")
    print(f"  expected conflicts: {prep.expected_conflicts}")
    print(f"  plan hash         : {prep.action_plan_hash}")
    print(f"  passed            : {prep.passed}")
    if getattr(prep, "error", None):
        print(f"  ERROR             : {prep.error}")

    print(f"\n=== DRY-RUN ({args.phase}) — TEMP COPY, no production write ===")
    dry = gate.dry_run(args.phase)
    print(f"  temp copy            : {dry.temp_copy}")
    print(f"  sha_before           : {dry.sha_before}")
    print(f"  sha_after            : {dry.sha_after}")
    print(f"  expected inserts     : {dry.expected_inserts}")
    print(f"  actual inserts       : {dry.actual_inserts}")
    print(f"  expected skips       : {dry.expected_skips}")
    print(f"  actual skips         : {dry.actual_skips}")
    print(f"  expected conflicts   : {dry.expected_conflicts}")
    print(f"  actual conflicts     : {dry.actual_conflicts}")
    print(f"  expected failures    : {dry.expected_failures}")
    print(f"  actual failures      : {dry.actual_failures}")
    print(f"  delta                : {dry.delta}")
    print(f"  side_effect_check    : {dry.side_effect_check}")
    print(f"  integrity_check      : {dry.integrity_check}")
    print(f"  matched              : {dry.matched}")
    print(f"  passed               : {dry.passed}")
    if getattr(dry, "error", None):
        print(f"  ERROR                : {dry.error}")

    print("\n=== HUMAN GATE (AGENTS.md rule 6) ===")
    print("  Dry-run output above. APPLY NOT RUN. Awaiting explicit human GO.")

    return 0 if dry.passed else 2


if __name__ == "__main__":
    sys.exit(main())
