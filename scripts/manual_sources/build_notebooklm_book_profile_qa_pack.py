import os
import csv
from datetime import datetime
from collections import Counter

CSV_DIR = "data/manual_sources/books/review_csv"
IN_ACCEPT = os.path.join(CSV_DIR, "book_profile_accept_preview.csv")
IN_MANUAL = os.path.join(CSV_DIR, "book_profile_manual_review.csv")
IN_NOT_FOUND = os.path.join(CSV_DIR, "book_profile_not_found.csv")
IN_BLOCKED = os.path.join(CSV_DIR, "book_profile_blocked.csv")

OUT_QA_PACK = os.path.join(CSV_DIR, "book_profile_qa_pack.csv")
OUT_CANDIDATE = os.path.join(CSV_DIR, "book_profile_apply_candidate_preview.csv")
REPORT_FILE = "output/reports/12x_notebooklm_book_profile_qa_pack_report.md"
GATE_FILE = "output/reports/12x_notebooklm_book_profile_qa_pack_gate.txt"

def load_csv(filepath, qa_decision):
    rows = []
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row['qa_decision'] = qa_decision
                row['review_decision'] = ""
                row['reviewer_note'] = ""
                rows.append(row)
    return rows

def write_csv(data_list, filepath):
    if not data_list:
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            pass
        return
        
    keys = list(data_list[0].keys())
    all_keys = set()
    for d in data_list: all_keys.update(d.keys())
    keys = [k for k in keys if k in all_keys] + [k for k in all_keys if k not in keys]
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data_list)

def main():
    accept = load_csv(IN_ACCEPT, "approve_candidate")
    manual = load_csv(IN_MANUAL, "needs_manual_review")
    not_found = load_csv(IN_NOT_FOUND, "needs_match_review")
    blocked = load_csv(IN_BLOCKED, "reject_blocked")
    
    all_rows = accept + manual + not_found + blocked
    
    candidates = []
    conflict_profile = 0
    radar_conflict = 0
    
    source_book_dist = Counter()
    match_strategy_dist = Counter()
    
    for row in all_rows:
        sb = row.get('source_book') or 'unknown'
        source_book_dist[sb] += 1
        ms = row.get('match_strategy', 'not_found')
        match_strategy_dist[ms] += 1
        
        c_fp = str(row.get('conflict_existing_profile', '')).lower() == 'true'
        r_c = str(row.get('radar_conflict', '')).lower() == 'true'
        if c_fp: conflict_profile += 1
        if r_c: radar_conflict += 1
        
        is_candidate = False
        if row['qa_decision'] == 'approve_candidate':
            notes = str(row.get('notes_for_manual_review', '')).lower()
            proxy_words = ["proxy", "based on", "not exact", "yerine"]
            has_proxy = any(pw in notes for pw in proxy_words)
            if not c_fp and not r_c and not has_proxy:
                is_candidate = True
                
        if is_candidate:
            candidates.append(row)
            
    write_csv(all_rows, OUT_QA_PACK)
    write_csv(candidates, OUT_CANDIDATE)
    
    os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
    
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("# NotebookLM Book Profile QA Pack Report\n\n")
        f.write(f"- generated_at: {datetime.now().isoformat()}\n")
        f.write(f"- total_rows: {len(all_rows)}\n")
        f.write(f"- approve_candidate: {len(accept)}\n")
        f.write(f"- needs_manual_review: {len(manual)}\n")
        f.write(f"- needs_match_review: {len(not_found)}\n")
        f.write(f"- reject_blocked: {len(blocked)}\n")
        f.write(f"- apply_candidate_preview: {len(candidates)}\n")
        f.write(f"- conflict_existing_profile_count: {conflict_profile}\n")
        f.write(f"- radar_conflict_count: {radar_conflict}\n")
        f.write(f"- not_found_count: {len(not_found)}\n\n")
        
        f.write("## Source/Book Dağılımı\n")
        for k, v in source_book_dist.items(): f.write(f"- {k}: {v}\n")
        
        f.write("\n## Match Strategy Dağılımı\n")
        for k, v in match_strategy_dist.items(): f.write(f"- {k}: {v}\n")
        
    with open(GATE_FILE, 'w', encoding='utf-8') as f:
        if len(blocked) > 0:
            f.write("BOOK_NOTEBOOKLM_QA_PACK_NO-GO\n")
        elif len(candidates) >= 1 and len(blocked) == 0:
            f.write("BOOK_NOTEBOOKLM_QA_PACK_GO_FOR_PROFILE_STAGING_DRY_RUN\n")
        elif len(candidates) == 0 and (len(manual) > 0 or len(not_found) > 0):
            f.write("BOOK_NOTEBOOKLM_QA_PACK_WARN_GO_REVIEW_ONLY\n")
        else:
            f.write("BOOK_NOTEBOOKLM_QA_PACK_NO-GO\n")
            
        f.write("PRODUCTION_IMPORT_NO-GO\n")
        
if __name__ == '__main__':
    main()
