import sqlite3
import os
import hashlib
import csv

DB_PATH = "output/import/production.db"
OUTPUT_DIR = "data/output"
DUPLICATE_CSV = os.path.join(OUTPUT_DIR, "final_tasting_notes_duplicate_risk.csv")
WEAK_CSV = os.path.join(OUTPUT_DIR, "final_tasting_notes_weak_content.csv")
COVERAGE_CSV = os.path.join(OUTPUT_DIR, "final_whisky_coverage_gap.csv")
REPORT_MD = "output/reports/final_production_tasting_notes_audit_report.md"

def get_file_hash(path):
    if not os.path.exists(path):
        return None
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def get_fingerprint(r):
    nose = str(r.get('nose_notes', '')).strip().lower()
    palate = str(r.get('palate_notes', '')).strip().lower()
    finish = str(r.get('finish_notes', '')).strip().lower()
    summary = str(r.get('notes_for_review', '')).strip().lower()
    content = f"{nose}|{palate}|{finish}|{summary}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def get_content_length(r):
    return len(str(r.get('nose_notes', ''))) + len(str(r.get('palate_notes', ''))) + len(str(r.get('finish_notes', '')))

def is_weak(r):
    nose_len = len(str(r.get('nose_notes', '')).strip())
    palate_len = len(str(r.get('palate_notes', '')).strip())
    finish_len = len(str(r.get('finish_notes', '')).strip())
    total_len = nose_len + palate_len + finish_len
    
    if total_len == 0: return True
    if nose_len < 25 or palate_len < 25 or finish_len < 15: return True
    if total_len < 80: return True
    if not str(r.get('source_url', '')).strip() and total_len < 120: return True
    
    return False

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    hash_before = get_file_hash(DB_PATH)
    conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    def safe_query(q, params=()):
        try:
            return [dict(r) for r in cur.execute(q, params).fetchall()]
        except sqlite3.OperationalError:
            return []

    tables = [r['name'] for r in safe_query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]

    # 1. Counts
    c_whiskies = len(safe_query("SELECT whisky_id FROM whiskies"))
    c_distilleries = len(safe_query("SELECT distillery_id FROM distilleries"))
    c_flavor = len(safe_query("SELECT whisky_id FROM flavor_profiles"))
    c_tasting = len(safe_query("SELECT rowid FROM tasting_notes"))
    c_staging_tasting = len(safe_query("SELECT rowid FROM staging_tasting_notes"))
    c_staging_book_flavor = len(safe_query("SELECT rowid FROM staging_book_flavor_profiles")) if 'staging_book_flavor_profiles' in tables else 0
    c_staging_queue = len(safe_query("SELECT rowid FROM staging_manual_review_queue")) if 'staging_manual_review_queue' in tables else 0

    # 2. Integrity
    integrity_res = cur.execute("PRAGMA integrity_check").fetchone()
    integrity_status = integrity_res[0] if integrity_res else "Failed"
    
    fk_tasting_missing = cur.execute("SELECT COUNT(*) FROM tasting_notes WHERE whisky_id NOT IN (SELECT whisky_id FROM whiskies)").fetchone()[0]
    fk_flavor_missing = cur.execute("SELECT COUNT(*) FROM flavor_profiles WHERE whisky_id NOT IN (SELECT whisky_id FROM whiskies)").fetchone()[0]
    tn_wid_missing = cur.execute("SELECT COUNT(*) FROM tasting_notes WHERE whisky_id IS NULL OR whisky_id = ''").fetchone()[0]
    fp_wid_missing = cur.execute("SELECT COUNT(*) FROM flavor_profiles WHERE whisky_id IS NULL OR whisky_id = ''").fetchone()[0]

    # 3. Source Distribution
    tasting_notes = safe_query("SELECT rowid, * FROM tasting_notes")
    source_sys_dist = {}
    source_url_missing = 0
    uploaded_count = 0
    
    for r in tasting_notes:
        s_sys = str(r.get('source_system', ''))
        s_url = str(r.get('source_url', ''))
        source_sys_dist[s_sys] = source_sys_dist.get(s_sys, 0) + 1
        if not s_url.strip():
            source_url_missing += 1
        if 'uploaded' in s_sys.lower() or 'uploaded' in str(r.get('source_name', '')).lower() or 'uploaded' in s_url.lower():
            uploaded_count += 1

    # 5. Duplicate Risk
    wid_notes = {}
    for r in tasting_notes:
        wid = str(r.get('whisky_id', ''))
        wid_notes.setdefault(wid, []).append(r)

    duplicate_risk_rows = []
    has_same_fp_duplicate = False
    for wid, notes in wid_notes.items():
        if len(notes) > 1:
            fps = {}
            for n in notes:
                fp = get_fingerprint(n)
                fps.setdefault(fp, []).append(n)
            
            for fp, group in fps.items():
                if len(group) > 1:
                    has_same_fp_duplicate = True
                    for n in group:
                        duplicate_risk_rows.append({
                            'whisky_id': wid,
                            'rowid': n.get('rowid'),
                            'source_system': n.get('source_system'),
                            'source_url': n.get('source_url'),
                            'risk_type': 'exact_fingerprint_match',
                            'risk_level': 'high'
                        })
                elif len(notes) > 1:
                    for n in group:
                        duplicate_risk_rows.append({
                            'whisky_id': wid,
                            'rowid': n.get('rowid'),
                            'source_system': n.get('source_system'),
                            'source_url': n.get('source_url'),
                            'risk_type': 'multiple_notes_for_whisky',
                            'risk_level': 'low'
                        })

    if duplicate_risk_rows:
        with open(DUPLICATE_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=duplicate_risk_rows[0].keys())
            writer.writeheader()
            writer.writerows(duplicate_risk_rows)

    # 6. Weak Content
    weak_rows = []
    for r in tasting_notes:
        if is_weak(r):
            weak_rows.append({
                'whisky_id': r.get('whisky_id'),
                'rowid': r.get('rowid'),
                'source_system': r.get('source_system'),
                'nose_len': len(str(r.get('nose_notes', ''))),
                'palate_len': len(str(r.get('palate_notes', ''))),
                'finish_len': len(str(r.get('finish_notes', ''))),
                'total_len': get_content_length(r),
                'has_url': bool(str(r.get('source_url', '')).strip())
            })

    if weak_rows:
        with open(WEAK_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=weak_rows[0].keys())
            writer.writeheader()
            writer.writerows(weak_rows)
            
    weak_uploaded_count = sum(1 for r in weak_rows if 'uploaded' in str(r.get('source_system', '')).lower())

    # 7. Coverage
    whiskies = {str(w.get('whisky_id')): w for w in safe_query("SELECT * FROM whiskies")}
    distilleries = {str(d.get('distillery_id')): d for d in safe_query("SELECT * FROM distilleries")}
    flavor_profiles = safe_query("SELECT whisky_id FROM flavor_profiles")
    fp_wids = set([str(f.get('whisky_id')) for f in flavor_profiles])
    tn_wids = set(wid_notes.keys())

    coverage_rows = []
    for wid, w in whiskies.items():
        has_tn = 'Yes' if wid in tn_wids else 'No'
        has_fp = 'Yes' if wid in fp_wids else 'No'
        dist_id = str(w.get('distillery_id', ''))
        dist_name = distilleries.get(dist_id, {}).get('name', 'Unknown')
        dist_region = distilleries.get(dist_id, {}).get('region', 'Unknown')
        
        coverage_rows.append({
            'whisky_id': wid,
            'whisky_name': w.get('name', w.get('normalized_name', '')),
            'distillery_name': dist_name,
            'region': dist_region,
            'has_tasting_note': has_tn,
            'has_flavor_profile': has_fp
        })

    with open(COVERAGE_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=coverage_rows[0].keys())
        writer.writeheader()
        writer.writerows(coverage_rows)

    c_tn_yes = sum(1 for c in coverage_rows if c['has_tasting_note'] == 'Yes')
    c_tn_no = c_whiskies - c_tn_yes
    c_fp_yes = sum(1 for c in coverage_rows if c['has_flavor_profile'] == 'Yes')
    c_fp_no = c_whiskies - c_fp_yes
    c_both = sum(1 for c in coverage_rows if c['has_tasting_note'] == 'Yes' and c['has_flavor_profile'] == 'Yes')
    c_neither = sum(1 for c in coverage_rows if c['has_tasting_note'] == 'No' and c['has_flavor_profile'] == 'No')

    # 8. Promotion Readiness
    staging_notes = safe_query("SELECT * FROM staging_tasting_notes")
    promo_dist = {}
    for sn in staging_notes:
        s_wid = str(sn.get('whisky_id', ''))
        app_status = str(sn.get('approval_status', '')).lower()
        if s_wid in tn_wids:
            promo_dist['already_in_production'] = promo_dist.get('already_in_production', 0) + 1
            continue
            
        if not s_wid or s_wid not in whiskies:
            promo_dist['blocked_fk_missing'] = promo_dist.get('blocked_fk_missing', 0) + 1
            continue
            
        if not str(sn.get('source_url', '')).strip():
            promo_dist['blocked_missing_source'] = promo_dist.get('blocked_missing_source', 0) + 1
            continue
            
        if app_status == 'needs_review' or app_status == 'pending':
            promo_dist['needs_content_review'] = promo_dist.get('needs_content_review', 0) + 1
            continue
            
        n_len = len(str(sn.get('nose', ''))) + len(str(sn.get('palate', ''))) + len(str(sn.get('finish', '')))
        if n_len < 80:
            promo_dist['needs_content_review'] = promo_dist.get('needs_content_review', 0) + 1
            continue
            
        promo_dist['promotion_ready'] = promo_dist.get('promotion_ready', 0) + 1

    conn.close()
    
    hash_after = get_file_hash(DB_PATH)
    hash_unchanged = (hash_before == hash_after)

    # 9. Write Report
    report = []
    report.append("# Final Production Tasting Notes Audit & Coverage Report\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    report.append(f"- **Hash Before:** `{hash_before}`")
    report.append(f"- **Hash After:** `{hash_after}`")
    report.append(f"- **Original DB Changed:** {'NO' if hash_unchanged else 'YES (MUTATION DETECTED!)'}")

    report.append("\n## Global Counts")
    report.append(f"- Whiskies: {c_whiskies}")
    report.append(f"- Distilleries: {c_distilleries}")
    report.append(f"- Flavor Profiles: {c_flavor}")
    report.append(f"- Tasting Notes: {c_tasting}")
    report.append(f"- Staging Tasting Notes: {c_staging_tasting}")
    report.append(f"- Staging Book Flavor Profiles: {c_staging_book_flavor}")
    report.append(f"- Staging Manual Review Queue: {c_staging_queue}")

    report.append("\n## Integrity Results")
    report.append(f"- PRAGMA integrity_check: {integrity_status}")
    report.append(f"- Tasting Notes FK Missing: {fk_tasting_missing}")
    report.append(f"- Flavor Profiles FK Missing: {fk_flavor_missing}")
    report.append(f"- Tasting Notes NULL Whisky ID: {tn_wid_missing}")
    report.append(f"- Flavor Profiles NULL Whisky ID: {fp_wid_missing}")

    report.append("\n## Source Distribution (Tasting Notes)")
    for k, v in source_sys_dist.items():
        report.append(f"- {k}: {v}")
    report.append(f"- Missing Source URL Count: {source_url_missing}")
    report.append(f"- Overall Uploaded Lineage Count: {uploaded_count}")

    report.append("\n## Cleanup Post-Check")
    report.append(f"- Exact Same Fingerprint Duplicates: {has_same_fp_duplicate}")
    report.append(f"- Weak Uploaded Content Remaining: {weak_uploaded_count}")

    report.append("\n## Duplicate Risk Summary")
    report.append(f"- Total Rows Flagged: {len(duplicate_risk_rows)}")
    report.append(f"- High Risk (Exact Fingerprint on same Whisky): {has_same_fp_duplicate}")

    report.append("\n## Weak Content Summary")
    report.append(f"- Total Weak Tasting Notes: {len(weak_rows)}")

    report.append("\n## Coverage Summary")
    report.append(f"- Whiskies With Tasting Notes: {c_tn_yes} ({c_tn_yes/c_whiskies*100:.1f}%)")
    report.append(f"- Whiskies Without Tasting Notes: {c_tn_no}")
    report.append(f"- Whiskies With Flavor Profiles: {c_fp_yes} ({c_fp_yes/c_whiskies*100:.1f}%)")
    report.append(f"- Whiskies Without Flavor Profiles: {c_fp_no}")
    report.append(f"- Whiskies With Both: {c_both}")
    report.append(f"- Whiskies With Neither: {c_neither}")

    # Top 20 coverage gaps (whiskies without either)
    gaps = [c for c in coverage_rows if c['has_tasting_note'] == 'No' and c['has_flavor_profile'] == 'No']
    report.append("\n## Top Coverage Gaps Sample (Missing Both)")
    report.append("| Whisky ID | Whisky Name | Distillery | Region |")
    report.append("|---|---|---|---|")
    for g in gaps[:20]:
        report.append(f"| {g['whisky_id']} | {g['whisky_name']} | {g['distillery_name']} | {g['region']} |")

    report.append("\n## Staging Promotion Readiness")
    for k, v in promo_dist.items():
        report.append(f"- {k}: {v}")

    report.append("\n## Recommended Next Phases")
    report.append("- **AŞAMA W — Promotion Candidate Pack v2**")
    report.append("- **AŞAMA X — Flavor Profile Coverage Expansion Plan**")
    report.append("- **AŞAMA Y — App Data QA Smoke Test**")

    report.append("\n## Final GO/NO-GO")
    is_go = hash_unchanged and integrity_status.lower() == 'ok' and fk_tasting_missing == 0 and fk_flavor_missing == 0
    if is_go:
        report.append("**GO** (Database is clean and structurally sound).")
    else:
        report.append("**NO-GO** (Integrity errors or hash mutations detected).")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))
        
    print(f"Report generated at: {REPORT_MD}")

if __name__ == "__main__":
    main()
