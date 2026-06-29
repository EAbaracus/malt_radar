import sqlite3
import os
import csv
import hashlib

DB_PATH = "output/import/production.db"
QUALITY_CSV = "data/output/book_extract_v2_quality_queue.csv"
QA_CSV = "data/output/book_extract_v2_candidate_qa_pack.csv"
REPORT_MD = "output/reports/book_extract_v2_candidate_qa_pack_report.md"

def main():
    os.makedirs(os.path.dirname(QA_CSV), exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    if not os.path.exists(QUALITY_CSV):
        print(f"Error: Quality CSV not found at {QUALITY_CSV}")
        return

    # Master index from production
    conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    whiskies = {str(w['whisky_id']): dict(w) for w in cur.execute("SELECT * FROM whiskies").fetchall()}
    existing_fps = {str(f['whisky_id']) for f in cur.execute("SELECT whisky_id FROM flavor_profiles").fetchall()}
    existing_tns = [dict(t) for t in cur.execute("SELECT * FROM tasting_notes").fetchall()]

    prod_tasting_note_fps = set()
    for tn in existing_tns:
        nose = str(tn.get('nose_notes', '')).strip().lower()
        palate = str(tn.get('palate_notes', '')).strip().lower()
        finish = str(tn.get('finish_notes', '')).strip().lower()
        fp = hashlib.md5(f"{nose}|{palate}|{finish}".encode('utf-8')).hexdigest()
        prod_tasting_note_fps.add(fp)

    conn.close()

    # Read candidates
    candidates = []
    with open(QUALITY_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            candidates.append(row)

    stats = {
        'total_candidates': len(candidates),
        'qa_ready_tasting_note': 0,
        'qa_ready_flavor_profile': 0,
        'qa_ready_both': 0,
        'manual_review': 0,
        'blocked_duplicate': 0,
        'blocked_existing_profile': 0,
        'blocked_other': 0
    }

    qa_pack = []

    for c in candidates:
        wid = str(c.get('whisky_id'))
        w_name = c.get('whisky_name')
        nose = c.get('nose_summary', '')
        palate = c.get('palate_summary', '')
        finish = c.get('finish_summary', '')
        origin = c.get('source_origin', '')
        
        # Parse radar scores
        scores = {}
        for axis in ['smoky', 'peaty', 'sherry', 'fruity', 'spicy', 'sweet', 'rich']:
            val_str = c.get(f'radar_{axis}', '0.0')
            try:
                scores[axis] = float(val_str)
            except ValueError:
                scores[axis] = 0.0

        confidence = 0.0
        try:
            confidence = float(c.get('extraction_confidence', '0.0'))
        except ValueError:
            pass

        # Validation flags
        fk_valid = wid in whiskies
        has_tasting_note_content = any([nose, palate, finish])
        
        # Check duplicate fingerprint
        content_fp = hashlib.md5(f"{nose.strip().lower()}|{palate.strip().lower()}|{finish.strip().lower()}".encode('utf-8')).hexdigest()
        is_dupe_tn = content_fp in prod_tasting_note_fps

        has_existing_profile = wid in existing_fps

        # Check radar scores constraints
        scores_valid = all(0.0 <= val <= 1.0 for val in scores.values())
        nonzero_axes = sum(1 for val in scores.values() if val > 0.0)
        axes_valid = nonzero_axes >= 2

        # Action logic
        action = 'block'
        reason = ''
        qa_status = 'Blocked'

        if not fk_valid:
            action = 'block'
            reason = 'Whisky ID not found in production database'
            stats['blocked_other'] += 1
        elif is_dupe_tn and has_existing_profile:
            action = 'block'
            reason = 'Duplicate tasting note and flavor profile already exists'
            stats['blocked_duplicate'] += 1
            stats['blocked_existing_profile'] += 1
        else:
            # Determine sub-actions
            tn_ready = fk_valid and has_tasting_note_content and not is_dupe_tn
            fp_ready = fk_valid and scores_valid and axes_valid and confidence >= 0.5 and not has_existing_profile

            if tn_ready and fp_ready:
                action = 'import_both'
                qa_status = 'Ready'
                reason = 'Tasting note and flavor profile are both QA Ready'
                stats['qa_ready_both'] += 1
            elif tn_ready:
                action = 'import_tasting_note'
                qa_status = 'Ready'
                reason = 'Tasting note is QA Ready'
                if has_existing_profile:
                    reason += ' (Flavor profile already exists)'
                    stats['blocked_existing_profile'] += 1
                elif not axes_valid:
                    reason += ' (Flavor profile lacks sufficient axes)'
                stats['qa_ready_tasting_note'] += 1
            elif fp_ready:
                action = 'import_flavor_profile'
                qa_status = 'Ready'
                reason = 'Flavor profile is QA Ready'
                if is_dupe_tn:
                    reason += ' (Tasting note already exists)'
                    stats['blocked_duplicate'] += 1
                stats['qa_ready_flavor_profile'] += 1
            else:
                action = 'manual_review'
                qa_status = 'Needs Review'
                reasons = []
                if is_dupe_tn: reasons.append('Duplicate tasting note content')
                if has_existing_profile: reasons.append('Whisky already has a flavor profile')
                if not axes_valid: reasons.append('Insufficient radar axes')
                reason = ", ".join(reasons)
                stats['manual_review'] += 1

        qa_row = dict(c)
        qa_row['qa_status'] = qa_status
        qa_row['qa_action'] = action
        qa_row['qa_reason'] = reason
        qa_pack.append(qa_row)

    # Write QA CSV
    if qa_pack:
        with open(QA_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=qa_pack[0].keys())
            writer.writeheader()
            writer.writerows(qa_pack)

    # Write MD Report
    report = []
    report.append("# Book Extract v2 Candidate QA Pack Report\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    
    report.append("\n## QA Processing Metrics")
    report.append(f"- Total Candidates Evaluated: {stats['total_candidates']}")
    report.append(f"- QA Ready - Tasting Note Only: {stats['qa_ready_tasting_note']}")
    report.append(f"- QA Ready - Flavor Profile Only: {stats['qa_ready_flavor_profile']}")
    report.append(f"- QA Ready - Both: {stats['qa_ready_both']}")
    report.append(f"- Needs Manual Review: {stats['manual_review']}")
    report.append(f"- Blocked (Duplicate Tasting Note): {stats['blocked_duplicate']}")
    report.append(f"- Blocked (Existing Flavor Profile): {stats['blocked_existing_profile']}")
    report.append(f"- Blocked (Invalid FK / Other): {stats['blocked_other']}")

    report.append("\n## Top 30 Mapped QA Ready Candidates")
    report.append("| Whisky ID | Whisky Name | Distillery | QA Status | Action | Reason |")
    report.append("|---|---|---|---|---|---|")
    ready_list = [r for r in qa_pack if r['qa_status'] == 'Ready']
    for r in ready_list[:30]:
        report.append(f"| {r['whisky_id']} | {r['whisky_name']} | {r['distillery_name']} | {r['qa_status']} | {r['qa_action']} | {r['qa_reason']} |")

    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Book extract v2 candidate QA pack successfully generated).")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD}")

if __name__ == "__main__":
    main()
