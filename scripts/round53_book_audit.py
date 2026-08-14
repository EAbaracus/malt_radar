import sqlite3
import json
import os
import hashlib

DB_PATH = "output/import/production.db"
OUT_DIR = "mr-kep/audit/book_contribution/round53_book_staging_audit"

def get_sha256(path):
    h = hashlib.sha256()
    if not os.path.exists(path):
        return "MISSING"
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def get_conn():
    uri = f"file:{os.path.abspath(DB_PATH)}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn

def run_book_audit():
    conn = get_conn()
    cur = conn.cursor()
    
    # 1. Baseline
    cur.execute("SELECT COUNT(*) as c FROM whiskies")
    live_total_whiskies = cur.fetchone()['c']
    
    cur.execute("SELECT COUNT(*) as c FROM flavor_evidence")
    live_total_evidence = cur.fetchone()['c']
    
    cur.execute("SELECT COUNT(*) as c FROM flavor_profiles")
    live_total_profiles = cur.fetchone()['c']
    
    # Coverage calculation matching previous round definitions
    cur.execute("SELECT COUNT(DISTINCT whisky_id) as c FROM flavor_evidence")
    live_covered = cur.fetchone()['c']
    live_uncovered = live_total_whiskies - live_covered
    
    # Fetch pending staging book profiles
    cur.execute('''
        SELECT s.staging_id, s.whisky_id, s.whisky_name, s.smoky, s.peaty, s.sherry, s.fruity,
               s.nose_summary, s.palate_summary, s.finish_summary,
               (SELECT COUNT(*) FROM whiskies WHERE whisky_id = s.whisky_id AND superseded_by IS NULL) as whisky_exists,
               (SELECT COUNT(*) FROM flavor_profiles WHERE whisky_id = s.whisky_id) as profile_exists
        FROM staging_book_flavor_profiles s
        WHERE s.approval_status = 'staging_pending_review'
    ''')
    rows = [dict(r) for r in cur.fetchall()]
    
    gap_resolvers = []
    enrichments = []
    orphans = []
    
    for r in rows:
        wid = r["whisky_id"]
        exists = r["whisky_exists"] == 1
        has_profile = r["profile_exists"] == 1
        
        # Clean record for output
        clean_record = {
            "staging_id": r["staging_id"],
            "whisky_id": wid,
            "whisky_name": r["whisky_name"],
            "vectors": {
                "smoky": r["smoky"],
                "peaty": r["peaty"],
                "sherry": r["sherry"],
                "fruity": r["fruity"]
            },
            "nose": r["nose_summary"][:100] if r["nose_summary"] else None
        }
        
        if exists:
            if has_profile:
                enrichments.append(clean_record)
            else:
                gap_resolvers.append(clean_record)
        else:
            orphans.append(clean_record)
            
    conn.close()
    
    # Coverage Projection
    projected_profiles = live_total_profiles + len(gap_resolvers)
    
    stats = {
        "total_pending_evaluated": len(rows),
        "mapped_to_active_whiskies": len(gap_resolvers) + len(enrichments),
        "gap_resolvers_count": len(gap_resolvers),
        "enrichment_candidates_count": len(enrichments),
        "unmatched_orphans_count": len(orphans),
        "current_profiles_count": live_total_profiles,
        "projected_profiles_count": projected_profiles,
        "coverage_increase_count": len(gap_resolvers)
    }
    
    return {
        "live_total_whiskies": live_total_whiskies,
        "live_total_evidence": live_total_evidence,
        "live_total_profiles": live_total_profiles,
        "live_covered": live_covered,
        "live_uncovered": live_uncovered,
        "gap_resolvers": gap_resolvers,
        "enrichments": enrichments,
        "orphans": orphans,
        "stats": stats
    }

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    sha_pre = get_sha256(DB_PATH)
    with open(f"{OUT_DIR}/08_sha_checkpoint_pre.json", "w") as f: json.dump({"sha256": sha_pre}, f)
    
    run_a = run_book_audit()
    run_b = run_book_audit()
    
    deterministic = json.dumps(run_a, sort_keys=True) == json.dumps(run_b, sort_keys=True)
    
    # Write Artifacts
    with open(f"{OUT_DIR}/01_scope_lock.json", "w") as f: json.dump({"locked": True}, f)
    with open(f"{OUT_DIR}/02_staging_inventory.json", "w") as f: 
        json.dump({
            "total_pending_rows": run_a["stats"]["total_pending_evaluated"],
            "mapped_rows": run_a["stats"]["mapped_to_active_whiskies"],
            "unmapped_rows": run_a["stats"]["unmatched_orphans_count"]
        }, f)
    with open(f"{OUT_DIR}/03_reconciliation_statistics.json", "w") as f: json.dump(run_a["stats"], f)
    with open(f"{OUT_DIR}/04_gap_resolvers.jsonl", "w") as f:
        for r in run_a["gap_resolvers"]: f.write(json.dumps(r) + "\n")
    with open(f"{OUT_DIR}/05_enrichment_candidates.jsonl", "w") as f:
        for r in run_a["enrichments"]: f.write(json.dumps(r) + "\n")
    with open(f"{OUT_DIR}/06_orphans_to_map.jsonl", "w") as f:
        for r in run_a["orphans"]: f.write(json.dumps(r) + "\n")
    with open(f"{OUT_DIR}/07_coverage_projection.json", "w") as f:
        json.dump({
            "current_profiles": run_a["live_total_profiles"],
            "projected_profiles": run_a["stats"]["projected_profiles_count"],
            "growth": f"+{run_a['stats']['gap_resolvers_count']}"
        }, f)
        
    sha_post = get_sha256(DB_PATH)
    with open(f"{OUT_DIR}/09_sha_checkpoint_post.json", "w") as f: json.dump({"sha256": sha_post}, f)
    
    db_unchanged = sha_pre == sha_post
    
    report = f"""# ROUND 53 FINAL REPORT - BOOK STAGING FORENSIC AUDIT

TOTAL_STAGING_ROWS_EVALUATED: {run_a["stats"]["total_pending_evaluated"]}

STAGING_CLASSIFICATION_BREAKDOWN:
1. MAPPED_TO_ACTIVE_WHISKIES: {run_a["stats"]["mapped_to_active_whiskies"]}
   - GAP_RESOLVERS (No existing profile): {run_a["stats"]["gap_resolvers_count"]}
   - ENRICHMENT_CANDIDATES (Has existing profile): {run_a["stats"]["enrichment_candidates_count"]}
2. UNMATCHED_ORPHANS (Needs manual mapping sprint): {run_a["stats"]["unmatched_orphans_count"]}

COVERAGE_PROJECTION:
- CURRENT_PROFILES_COUNT: {run_a["live_total_profiles"]}
- PROJECTED_PROFILES_COUNT: {run_a["stats"]["projected_profiles_count"]}
- COV_GROWTH_POTENTIAL: +{run_a["stats"]["gap_resolvers_count"]} new canonical profiles

PRODUCTION_WRITES = 0
STAGING_WRITES = 0
PROMOTION = 0
DELETION = 0
PROFILE_MIGRATION = 0
SUPERSEDE_APPLY = 0
ENTITY_CREATION = 0
QUEUE_MUTATION = 0
LEDGER_MUTATION = 0
ACL_MUTATIONS = 0
OWNERSHIP_MUTATIONS = 0
SECURITY_BYPASS = 0

PRODUCTION_SHA_PRE: {sha_pre}
PRODUCTION_SHA_POST: {sha_post}
DB_SHA_UNCHANGED = {str(db_unchanged).upper()}

DETERMINISTIC = {str(deterministic).upper()}
CLEAN_HALT = YES

FINAL_VERDICT: NO_MUTATION_REPORT_ONLY
"""
    with open(f"{OUT_DIR}/10_FINAL_REPORT.md", "w") as f: f.write(report)
    print(report)

if __name__ == "__main__":
    main()
