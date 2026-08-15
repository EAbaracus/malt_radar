import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "output" / "import" / "production.db"
QUARANTINE_PATH = ROOT / "mr-kep" / "audit" / "quarantine" / "data_quality_quarantine_v1.jsonl"

def run_dry_run():
    if not DB_PATH.exists():
        print(f"Error: DB file not found at {DB_PATH}")
        return

    pre_sha = hashlib.sha256(DB_PATH.read_bytes()).hexdigest().upper()
    print(f"Pre-dry-run SHA256: {pre_sha}")

    entries = []
    if QUARANTINE_PATH.exists():
        with open(QUARANTINE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line.strip()))

    synthetic_count = sum(1 for e in entries if e.get("quarantine_reason") == "synthetic_webcrawl_round88_template")
    smws_count = sum(1 for e in entries if e.get("quarantine_reason") == "zero_tasting_notes_empty_profile")

    print(f"Loaded quarantine package: {len(entries)} total entries")
    print(f"  - Synthetic template entries: {synthetic_count}")
    print(f"  - Empty SMWS entries: {smws_count}")

    post_sha = hashlib.sha256(DB_PATH.read_bytes()).hexdigest().upper()
    assert pre_sha == post_sha, "CRITICAL: Dry-run mutated production.db!"
    print(f"Post-dry-run SHA256: {post_sha} (MATCH - ZERO WRITES)")

if __name__ == "__main__":
    run_dry_run()
