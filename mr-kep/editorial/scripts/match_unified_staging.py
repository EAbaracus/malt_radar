"""Run WhiskyRegistryMatcher over all unified staging rows and persist the
match decision back into the STAGING DB (staging-only write).

Production.db is opened mode=ro ONLY — never written.

Usage:
    python mr-kep/editorial/scripts/match_unified_staging.py \
        --staging output/staging/unified_staging.db \
        [--production output/import/production.db]

Updates columns: matched_master_whisky_id, match_status, match_confidence.
Re-runnable (idempotent).
"""
import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "mr-kep"))

from editorial.matching import WhiskyRegistryMatcher  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--staging", default=str(ROOT / "output/staging/unified_staging.db"))
    ap.add_argument("--production", default=str(ROOT / "output/import/production.db"))
    args = ap.parse_args()

    matcher = WhiskyRegistryMatcher(args.production)
    n_master = matcher.load_registry()
    print(f"production master whiskies: {n_master} (read-only)")

    conn = sqlite3.connect(args.staging)
    rows = conn.execute(
        "SELECT evidence_id, raw_name, metadata_json FROM staging_editorial_reviews"
    ).fetchall()

    counts = {}
    total = len(rows)
    for eid, raw_name, meta_json in rows:
        age_hint = None
        if meta_json:
            import json
            try:
                age_hint = json.loads(meta_json).get("age")
            except Exception:
                pass
        d = matcher.match(raw_name, age_hint)
        counts[d.match_status] = counts.get(d.match_status, 0) + 1
        conn.execute(
            "UPDATE staging_editorial_reviews SET matched_master_whisky_id=?, "
            "match_status=?, match_confidence=? WHERE evidence_id=?",
            (d.matched_master_whisky_id, d.match_status, d.match_confidence, eid),
        )
    conn.commit()
    conn.close()

    print(f"\nMATCH RESULTS ({total} rows):")
    for status in ("exact", "fuzzy", "manual_review", "unmatched"):
        print(f"  {status:14s} {counts.get(status, 0)}")
    promotable = counts.get("exact", 0) + counts.get("fuzzy", 0)
    print(f"\nPROMOTABLE (exact+fuzzy): {promotable} | needs human review: {total - promotable}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
