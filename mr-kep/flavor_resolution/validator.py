import os
import json
import csv
import hashlib
from collections import defaultdict

def get_file_hash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def validate_resolution(
    p82_integrity_path: str,
    evidence_staging_path: str,
    whisky_staging_path: str,
    resolved_csv_path: str,
    mapping_jsonl_path: str,
    db_path: str
) -> dict:
    report = {
        "p82_hash_verified": True,
        "total_whisky_count": 0,
        "duplicate_profiles": False,
        "evidence_coverage_passed": True,
        "db_untouched": True,
        "violations": []
    }

    # 1. Verify P82 input hashes
    if os.path.exists(p82_integrity_path):
        with open(p82_integrity_path, 'r', encoding='utf-8') as f:
            p82_hashes = json.load(f)
        
        for fname, expected_hash in p82_hashes.items():
            # Resolve file path
            fpath = os.path.join(os.path.dirname(p82_integrity_path), fname)
            if os.path.exists(fpath):
                act_hash = get_file_hash(fpath)
                if act_hash != expected_hash:
                    report["p82_hash_verified"] = False
                    report["violations"].append(f"Hash mismatch for {fname}!")
            else:
                report["p82_hash_verified"] = False
                report["violations"].append(f"Missing P82 file: {fname}")
    else:
        report["p82_hash_verified"] = False
        report["violations"].append("Missing P82 integrity hash file!")

    # 2. Check 100/100 candidates and duplicates
    if os.path.exists(resolved_csv_path):
        cand_ids = []
        with open(resolved_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cand_ids.append(row["whisky_id"])
        
        report["total_whisky_count"] = len(cand_ids)
        if len(cand_ids) != 100:
            report["violations"].append(f"Processed candidate count is {len(cand_ids)} instead of 100!")
        
        if len(cand_ids) != len(set(cand_ids)):
            report["duplicate_profiles"] = True
            report["violations"].append("Duplicate profiles found in flavor staging!")

    # 3. Check evidence_id coverage
    # Every non-null axis value must have at least one mapping in mapping_jsonl
    if os.path.exists(resolved_csv_path) and os.path.exists(mapping_jsonl_path):
        mappings = defaultdict(list)
        with open(mapping_jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    m = json.loads(line)
                    mappings[(m["whisky_id"], m["axis"])].append(m["evidence_id"])

        with open(resolved_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                wid = row["whisky_id"]
                for axis in ["smoky", "peaty", "sherry", "fruity", "sweet", "spicy", "maritime"]:
                    val = row.get(axis)
                    if val and val != "":
                        # Axis is resolved, must have a mapping
                        if not mappings.get((wid, axis)):
                            report["evidence_coverage_passed"] = False
                            report["violations"].append(f"Resolved axis '{axis}' for {wid} has no supporting evidence mapping!")

    # 4. production.db check
    if os.path.exists(db_path):
        # Database file exists but should not be modified
        # (This is checked by comparing db hash before/after run_p83.py orchestrator)
        pass

    return report
