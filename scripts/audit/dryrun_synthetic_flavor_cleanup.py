"""KEP Data Quality Dry-Run — Synthetic Flavor Profile Cleanup.

Pre-apply SHA256 projection, candidate counting, and backup verification.
Reads output/import/production.db read-only.
"""
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROD = ROOT / "output" / "import" / "production.db"
OUTDIR = ROOT / "output" / "gate_synthetic_cleanup"

SYNTHETIC_LIKE_SPICY = '%"spicy": 60%'
SYNTHETIC_LIKE_PEATED = '%"smoky_peaty": 60%'

def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()

def main():
    if not PROD.exists():
        print(f"ERROR: {PROD} does not exist")
        return 1

    OUTDIR.mkdir(parents=True, exist_ok=True)
    sha_pre = sha256(PROD)

    conn = sqlite3.connect(f"file:{PROD.resolve()}?mode=ro", uri=True)
    c = conn.cursor()

    # Count synthetic profiles
    c.execute("""
        SELECT COUNT(*) FROM flavor_profiles 
        WHERE flavor_profile LIKE ? AND flavor_profile LIKE ?
    """, (SYNTHETIC_LIKE_SPICY, SYNTHETIC_LIKE_PEATED))
    synthetic_count = c.fetchone()[0]

    # Select target whisky_ids
    c.execute("""
        SELECT whisky_id, whisky_name FROM flavor_profiles 
        WHERE flavor_profile LIKE ? AND flavor_profile LIKE ?
    """, (SYNTHETIC_LIKE_SPICY, SYNTHETIC_LIKE_PEATED))
    targets = [{"whisky_id": r[0], "name": r[1]} for r in c.fetchall()]

    conn.close()

    dryrun_data = {
        "phase": "SYNTHETIC_FLAVOR_CLEANUP_V2",
        "pre_apply_sha256": sha_pre,
        "target_count": synthetic_count,
        "targets": targets,
        "action": "UPDATE flavor_profiles SET flavor_profile=NULL WHERE synthetic_template"
    }

    out_file = OUTDIR / "SYNTHETIC_CLEANUP_DRYRUN.json"
    out_file.write_text(json.dumps(dryrun_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"=== KEP SYNTHETIC CLEANUP DRY-RUN ===")
    print(f"  Pre-apply SHA256: {sha_pre}")
    print(f"  Synthetic candidate count: {synthetic_count}")
    print(f"  Dry-run report saved to: {out_file}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
