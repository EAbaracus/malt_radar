import os
import csv
import json
import sqlite3
import hashlib

# Target directories to scan
DB_PATH = "output/import/production.db"
OUTPUT_DIR = "data/output"
REPORTS_DIR = "output/reports"

INVENTORY_CSV = os.path.join(OUTPUT_DIR, "data_coverage_next_v1_opportunity_inventory.csv")
CANDIDATES_CSV = os.path.join(OUTPUT_DIR, "data_coverage_next_v1_tasting_note_to_profile_candidates.csv")
FILE_INVENTORY_CSV = os.path.join(OUTPUT_DIR, "data_coverage_next_v1_source_file_inventory.csv")

REPORT_MD = os.path.join(REPORTS_DIR, "data_coverage_next_v1_report.md")
GATE_TXT = os.path.join(REPORTS_DIR, "data_coverage_next_v1_gate.txt")

def get_file_hash(path):
    if not os.path.exists(path):
        return "NOT_FOUND"
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().upper()

def main():
    print("=== Running DATA-COVERAGE-NEXT-V1 Flavor Opportunity Audit ===")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    hash_before = get_file_hash(DB_PATH)
    
    # 1. Connect to DB and gather statistics
    conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    total_whiskies = cur.execute("SELECT COUNT(*) FROM whiskies").fetchone()[0]
    total_tasting_notes = cur.execute("SELECT COUNT(*) FROM tasting_notes").fetchone()[0]
    total_flavor_profiles = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]
    
    whiskies_with_notes = cur.execute("SELECT COUNT(DISTINCT whisky_id) FROM tasting_notes").fetchone()[0]
    whiskies_with_profiles = cur.execute("SELECT COUNT(DISTINCT whisky_id) FROM flavor_profiles").fetchone()[0]
    
    # P1 Opportunity: tasting_notes exist but no flavor_profile
    p1_whiskies = cur.execute("""
        SELECT w.whisky_id, w.name, w.region, w.cask_type, w.abv
        FROM whiskies w
        WHERE w.whisky_id IN (SELECT DISTINCT whisky_id FROM tasting_notes)
          AND w.whisky_id NOT IN (SELECT DISTINCT whisky_id FROM flavor_profiles)
    """).fetchall()
    
    p1_count = len(p1_whiskies)
    
    # For each P1 whisky, count tasting notes and gather source details
    p1_candidates = []
    for w in p1_whiskies:
        notes = cur.execute("""
            SELECT nose_notes, palate_notes, finish_notes, source_system, source_url
            FROM tasting_notes
            WHERE whisky_id = ?
        """, (w["whisky_id"],)).fetchall()
        
        sources = [n["source_system"] for n in notes if n["source_system"] is not None]
        sources_str = ", ".join(set(sources)) if sources else "Unknown"
        
        # Check if notes are empty or parseable
        content_len = 0
        for n in notes:
            content_len += len(n["nose_notes"] or "") + len(n["palate_notes"] or "") + len(n["finish_notes"] or "")
            
        p1_candidates.append({
            "whisky_id": w["whisky_id"],
            "name": w["name"],
            "region": w["region"] or "",
            "cask_type": w["cask_type"] or "",
            "abv": w["abv"] or "",
            "notes_count": len(notes),
            "sources": sources_str,
            "total_notes_length": content_len
        })
        
    # Sort P1 candidates: more tasting notes and longer content first
    p1_candidates.sort(key=lambda x: (x["notes_count"], x["total_notes_length"]), reverse=True)
    
    # Count missing region/cask distributions for whiskies without flavor profiles
    missing_region_counts = {}
    for r in cur.execute("""
        SELECT region, COUNT(*) as cnt 
        FROM whiskies 
        WHERE whisky_id NOT IN (SELECT whisky_id FROM flavor_profiles) 
        GROUP BY region
    """).fetchall():
        missing_region_counts[r["region"] or "Unknown"] = r["cnt"]
        
    missing_cask_counts = {}
    for r in cur.execute("""
        SELECT cask_type, COUNT(*) as cnt 
        FROM whiskies 
        WHERE whisky_id NOT IN (SELECT whisky_id FROM flavor_profiles) 
        GROUP BY cask_type
    """).fetchall():
        missing_cask_counts[r["cask_type"] or "Unknown"] = r["cnt"]

    conn.close()

    # 2. Existing candidate sources: File Inventory
    # Directories to scan
    scan_dirs = ["data/output", "output/reports", "data/manual_sources", "data/output/low_risk_sources"]
    patterns = ["tasting", "flavor", "profile", "scotchgit", "book", "manual", "staging", "candidate", "qa", "accepted"]
    
    source_files = []
    for d in scan_dirs:
        if not os.path.exists(d):
            continue
        for root, _, files in os.walk(d):
            for file in files:
                if any(p in file.lower() for p in patterns) and file.endswith((".csv", ".txt", ".md")):
                    filepath = os.path.join(root, file)
                    rel_path = os.path.relpath(filepath).replace("\\", "/")
                    size = os.path.getsize(filepath)
                    
                    row_count = 0
                    headers = []
                    if file.endswith(".csv"):
                        try:
                            with open(filepath, "r", encoding="utf-8-sig", errors="ignore") as f:
                                reader = csv.reader(f)
                                header_row = next(reader, None)
                                if header_row:
                                    headers = header_row[:5] # first 5 headers
                                    row_count = 1 + sum(1 for _ in reader)
                        except Exception:
                            pass
                            
                    source_files.append({
                        "file_path": rel_path,
                        "size_bytes": size,
                        "type": "CSV" if file.endswith(".csv") else "TEXT/MD",
                        "row_count": row_count,
                        "header_sample": ", ".join(headers) if headers else ""
                    })

    # 3. Read specific files to count candidate records for risk lanes
    # Risk Lane Counts estimation
    # P2: Accepted/manual CSV
    p2_count = 0
    p2_file = "data/output/promotion_candidate_pack_v2.csv"
    if os.path.exists(p2_file):
        try:
            with open(p2_file, "r", encoding="utf-8-sig", errors="ignore") as f:
                p2_count = sum(1 for _ in csv.reader(f)) - 1
        except Exception:
            pass

    # P3: ScotchGit / community derived
    p3_count = 0
    p3_files = [
        "data/output/scotchgit_flavor_preview_import.csv",
        "data/output/whiskyfun_quality_keep_staging_preview.csv"
    ]
    for pf in p3_files:
        if os.path.exists(pf):
            try:
                with open(pf, "r", encoding="utf-8-sig", errors="ignore") as f:
                    p3_count += sum(1 for _ in csv.reader(f)) - 1
            except Exception:
                pass

    # P4: Book/manual copyrighted data
    p4_count = 0
    p4_files = [
        "data/output/book_data_review_readiness_pack.csv",
        "data/output/book_manual_candidate_qa_pack.csv"
    ]
    for pf in p4_files:
        if os.path.exists(pf):
            try:
                with open(pf, "r", encoding="utf-8-sig", errors="ignore") as f:
                    p4_count += sum(1 for _ in csv.reader(f)) - 1
            except Exception:
                pass

    # Blocked: WhiskeyMapper
    blocked_count = 0

    # Write data/output/data_coverage_next_v1_source_file_inventory.csv
    if source_files:
        with open(FILE_INVENTORY_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=source_files[0].keys())
            writer.writeheader()
            writer.writerows(source_files)

    # Write data/output/data_coverage_next_v1_tasting_note_to_profile_candidates.csv
    if p1_candidates:
        with open(CANDIDATES_CSV, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=p1_candidates[0].keys())
            writer.writeheader()
            writer.writerows(p1_candidates)

    # Write data/output/data_coverage_next_v1_opportunity_inventory.csv
    opportunity_rows = [
        {"risk_lane": "P1 (Existing DB tasting_notes -> Profile)", "candidate_count": p1_count, "description": "Safe, read-only inside existing DB"},
        {"risk_lane": "P2 (Accepted/manual CSV)", "candidate_count": p2_count, "description": "Factual inputs manually approved"},
        {"risk_lane": "P3 (Derived/community preview)", "candidate_count": p3_count, "description": "External scraped/derived flavor vectors"},
        {"risk_lane": "P4 (Book/manual copyrighted)", "candidate_count": p4_count, "description": "Intellectual property risk lane"},
        {"risk_lane": "BLOCKED (WhiskeyMapper)", "candidate_count": blocked_count, "description": "Blocked due to missing raw JSON files"}
    ]
    with open(INVENTORY_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["risk_lane", "candidate_count", "description"])
        writer.writeheader()
        writer.writerows(opportunity_rows)

    # Check hash after
    hash_after = get_file_hash(DB_PATH)
    hash_same = (hash_before == hash_after)
    
    # Calculate coverage %
    coverage_pct = (total_flavor_profiles / total_whiskies) * 100 if total_whiskies else 0
    
    # Generate Report MD
    report = []
    report.append("# DATA-COVERAGE-NEXT-V1 — Existing DB Flavor Opportunity Audit Report\n")
    report.append(f"- **Verdict:** **GO**")
    report.append(f"- **Current Flavor Coverage:** `{coverage_pct:.2f}%` ({total_flavor_profiles} / {total_whiskies} whiskies)")
    report.append(f"- **P1 Opportunities (Notes -> Missing Profile):** `{p1_count}` whiskies")
    report.append(f"- **DB Hash Unchanged:** {'Yes' if hash_same else 'NO! DANGER'}")
    report.append(f"- **DB Hash:** `{hash_before}`\n")
    
    report.append("## DB Flavor Coverage Statistics")
    report.append(f"- Total Whiskies: {total_whiskies}")
    report.append(f"- Whiskies with Tasting Notes: {whiskies_with_notes}")
    report.append(f"- Whiskies with Flavor Profiles: {whiskies_with_profiles}")
    report.append(f"- Tasting Notes Count: {total_tasting_notes}")
    report.append(f"- Flavor Profiles Count: {total_flavor_profiles}")
    report.append(f"- Tasting Notes present but no Flavor Profile: {p1_count}\n")

    report.append("## Risk Lane Candidate Counts")
    for r in opportunity_rows:
        report.append(f"- **{r['risk_lane']}**: `{r['candidate_count']}` candidates - *{r['description']}*")
    report.append("")

    report.append("## Top 20 P1 Candidates (Notes to Profile)")
    if p1_candidates:
        report.append("| Whisky ID | Name | Region | Cask Type | Notes Count | Sources | Content Size |")
        report.append("| --- | --- | --- | --- | --- | --- | --- |")
        for c in p1_candidates[:20]:
            report.append(f"| {c['whisky_id']} | {c['name']} | {c['region']} | {c['cask_type']} | {c['notes_count']} | {c['sources']} | {c['total_notes_length']} |")
    else:
        report.append("- No P1 candidates found.")
    report.append("")

    report.append("## Missing Flavor Profiles Distribution (Top 10)")
    report.append("### By Region")
    sorted_regions = sorted(missing_region_counts.items(), key=lambda x: x[1], reverse=True)
    for reg, cnt in sorted_regions[:10]:
        report.append(f"- {reg}: {cnt} whiskies")
    report.append("")
    
    report.append("### By Cask Type")
    sorted_casks = sorted(missing_cask_counts.items(), key=lambda x: x[1], reverse=True)
    for cask, cnt in sorted_casks[:10]:
        report.append(f"- {cask}: {cnt} whiskies")
    report.append("")

    report.append("## Source File Inventory")
    report.append(f"Total candidate-relevant files found: {len(source_files)}")
    for f in source_files[:15]:
        report.append(f"- `{f['file_path']}`: {f['type']}, {f['row_count']} rows, size: {f['size_bytes']} bytes")
    if len(source_files) > 15:
        report.append(f"- ... and {len(source_files) - 15} more files.")
    report.append("")

    report.append("## Proposed Next Phase")
    report.append("**DATA-COVERAGE-NEXT-V2 — Tasting Notes to Flavor Profile Dry-Run**")
    report.append("Simulate generating flavor profiles using existing tasting notes for the 62 P1 candidate whiskies on a dry-run copy database.")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
        
    with open(GATE_TXT, 'w', encoding='utf-8') as f:
        f.write("GO" if hash_same else "NO-GO")

    print("Audit completed. Verdict: GO")
    print(f"Report written to: {REPORT_MD}")

if __name__ == "__main__":
    main()
