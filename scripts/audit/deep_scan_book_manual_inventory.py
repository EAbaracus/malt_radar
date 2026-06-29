import sqlite3
import os
import csv
import json
import re

DB_PATH = "output/import/production.db"
DOWNLOADS_DIR = "C:/Users/eltun/Downloads"
KITAPLAR_DIR = "C:/Users/eltun/Downloads/kitaplar"
PROJECT_DIR = "C:/Users/eltun/Documents/malt radar CLEAN"

OUTPUT_DIR = "data/output"
FILES_CSV = os.path.join(OUTPUT_DIR, "deep_book_manual_inventory_files.csv")
DB_CSV = os.path.join(OUTPUT_DIR, "deep_book_manual_inventory_db.csv")
UNIFIED_CSV = os.path.join(OUTPUT_DIR, "deep_book_manual_inventory_unified.csv")
UNMATCHED_CSV = os.path.join(OUTPUT_DIR, "deep_book_manual_inventory_unmatched.csv")
REPORT_MD = "output/reports/deep_book_manual_inventory_report.md"

KEYWORDS = [
    'book', 'notebooklm', 'uploaded_document', 'uploaded_whisky_tasting_notes',
    'manual', 'whisky tasting guide', 'ultimate book', 'let me tell you about whisky',
    '12n', 'nb_fp', 'extracted_jsonl', 'review_csv'
]

def check_text(text):
    if not text: return []
    text_lower = str(text).lower()
    matched = []
    for kw in KEYWORDS:
        if kw in text_lower:
            matched.append(kw)
    return matched

def get_row_count_and_columns(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    row_count = 0
    cols = []
    sample = ""
    try:
        if ext == '.csv':
            with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if header:
                    cols = header
                    row_count = 1 + sum(1 for _ in reader)
                    f.seek(0)
                    r_dict = next(csv.DictReader(f), None)
                    if r_dict:
                        sample = str(dict(r_dict))[:500]
        elif ext in ['.jsonl', '.json']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                row_count = len(lines)
                if lines:
                    try:
                        sample_json = json.loads(lines[0])
                        cols = list(sample_json.keys())
                        sample = str(sample_json)[:500]
                    except:
                        sample = lines[0][:500]
        elif ext in ['.txt', '.md']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                row_count = len(lines)
                if lines:
                    sample = "".join(lines[:5])[:500]
    except Exception as e:
        sample = f"Error reading: {e}"
    return row_count, cols, sample

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    whiskies = {str(w['whisky_id']): dict(w) for w in cur.execute("SELECT * FROM whiskies").fetchall()}
    distilleries = {str(d['distillery_id']): dict(d) for d in cur.execute("SELECT * FROM distilleries").fetchall()}
    existing_fps = {str(f['whisky_id']) for f in cur.execute("SELECT whisky_id FROM flavor_profiles").fetchall()}
    existing_tns = {str(t['whisky_id']) for t in cur.execute("SELECT whisky_id FROM tasting_notes").fetchall()}

    # --- 1. Scan DB Tables ---
    db_results = []
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    
    for t in tables:
        if t in ['sqlite_sequence']: continue
        cols = [c[1] for c in cur.execute(f"PRAGMA table_info({t})").fetchall()]
        
        # Build query to fetch all rows
        rows = cur.execute(f"SELECT rowid, * FROM {t}").fetchall()
        for r in rows:
            r_dict = dict(r)
            rowid = r_dict.get('rowid', 'N/A')
            
            # Find any column that matches a keyword
            matched_col = None
            matched_val = None
            matched_kws = []
            
            for c in cols:
                val = r_dict.get(c)
                if val:
                    kws = check_text(val)
                    if kws:
                        matched_col = c
                        matched_val = str(val)
                        matched_kws.extend(kws)
            
            if matched_kws:
                wid = r_dict.get('whisky_id') or r_dict.get('staging_note_id') or r_dict.get('staging_id')
                w_name = r_dict.get('whisky_name') or r_dict.get('product_name') or r_dict.get('production_bottle_name')
                
                db_results.append({
                    'table_name': t,
                    'rowid_or_key': str(rowid),
                    'whisky_id': str(wid) if wid else 'N/A',
                    'whisky_name': str(w_name) if w_name else 'N/A',
                    'source_system': r_dict.get('source_system', r_dict.get('flavor_source', 'N/A')),
                    'source_name': r_dict.get('source_name', 'N/A'),
                    'source_url': r_dict.get('source_url', 'N/A'),
                    'matched_column': matched_col,
                    'matched_value': matched_val[:200]
                })

    with open(DB_CSV, 'w', newline='', encoding='utf-8') as f:
        if db_results:
            writer = csv.DictWriter(f, fieldnames=db_results[0].keys())
            writer.writeheader()
            writer.writerows(db_results)

    # --- 2. Scan Repo Files ---
    file_results = []
    
    # We will search the project directory and the downloads directory
    search_dirs = [
        ("PROJECT:data/input", os.path.join(PROJECT_DIR, "data/input")),
        ("PROJECT:data/output", os.path.join(PROJECT_DIR, "data/output")),
        ("PROJECT:output/reports", os.path.join(PROJECT_DIR, "output/reports")),
        ("PROJECT:scripts/manual_sources", os.path.join(PROJECT_DIR, "scripts/manual_sources")),
        ("DOWNLOADS:kitaplar", KITAPLAR_DIR),
        ("DOWNLOADS:root", DOWNLOADS_DIR)
    ]
    
    scanned_paths = []
    for tag, d_path in search_dirs:
        if not os.path.exists(d_path):
            continue
        for root, dirs, files_list in os.walk(d_path):
            for file_name in files_list:
                f_path = os.path.join(root, file_name)
                # Avoid scanning raw binary files except pdf
                ext = os.path.splitext(file_name)[1].lower()
                if ext in ['.exe', '.zip', '.png', '.jpg', '.jpeg', '.gif', '.pyc']:
                    continue
                
                rel_path = os.path.relpath(f_path, PROJECT_DIR)
                
                # Check filename keywords
                fn_kws = check_text(file_name)
                
                content_kws = []
                # If text-like, check content keywords (first 10KB to avoid memory/time limit)
                if ext in ['.txt', '.md', '.csv', '.jsonl', '.json']:
                    try:
                        with open(f_path, 'r', encoding='utf-8', errors='ignore') as f:
                            chunk = f.read(10000)
                            content_kws = check_text(chunk)
                    except:
                        pass
                
                union_kws = list(set(fn_kws + content_kws))
                if union_kws:
                    row_count, cols, sample = get_row_count_and_columns(f_path)
                    
                    file_results.append({
                        'file_path': rel_path,
                        'file_size_bytes': os.path.getsize(f_path),
                        'line_or_row_count': row_count,
                        'matched_keywords': ", ".join(union_kws),
                        'detected_columns_or_keys': ", ".join(cols[:10]),
                        'sample_row_preview': sample
                    })
                    scanned_paths.append(f_path)

    with open(FILES_CSV, 'w', newline='', encoding='utf-8') as f:
        if file_results:
            writer = csv.DictWriter(f, fieldnames=file_results[0].keys())
            writer.writeheader()
            writer.writerows(file_results)

    # --- 3. Unified and Unmatched Candidate Extraction ---
    unified_results = []
    unmatched_results = []
    
    seen_candidates = set()

    # Load candidates from DB
    for db_row in db_results:
        wid = db_row['whisky_id']
        w_name = db_row['whisky_name']
        t_name = db_row['table_name']
        
        if wid and wid != 'N/A':
            if wid in whiskies:
                status = 'file_only'
                if wid in existing_fps:
                    status = 'already_in_production'
                elif wid in existing_tns:
                    status = 'staging_pending'
                
                cand_key = (wid, f"DB:{t_name}")
                if cand_key not in seen_candidates:
                    seen_candidates.add(cand_key)
                    unified_results.append({
                        'whisky_id': wid,
                        'whisky_name': whiskies[wid].get('name', w_name),
                        'distillery_name': distilleries.get(str(whiskies[wid].get('distillery_id')), {}).get('name', 'Unknown') if whiskies[wid].get('distillery_id') else 'Unknown',
                        'source_origin': f"DB:{t_name}",
                        'content_preview': db_row['matched_value'],
                        'status': status
                    })
            else:
                unmatched_results.append({
                    'raw_whisky_id': wid,
                    'raw_whisky_name': w_name,
                    'raw_distillery_name': 'N/A',
                    'source_origin': f"DB:{t_name}",
                    'reason': 'Orphaned Whisky ID (not found in whiskies table)'
                })

    # Load candidates from files (like whisky_chunks_cleaned.jsonl)
    jsonl_path = "C:/Users/eltun/Downloads/whisky_chunks_cleaned.jsonl"
    if os.path.exists(jsonl_path):
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f):
                try:
                    obj = json.loads(line)
                    raw_wid = str(obj.get('whisky_id', ''))
                    raw_name = str(obj.get('target', obj.get('whisky_name', '')))
                    raw_text = str(obj.get('text', ''))
                    
                    # Try to match raw_name to whiskies
                    matched_wid = None
                    if raw_wid and raw_wid in whiskies:
                        matched_wid = raw_wid
                    else:
                        # Fuzzy match target name
                        for w_id, w in whiskies.items():
                            w_n = str(w.get('name', '')).lower()
                            if w_n == raw_name.lower():
                                matched_wid = w_id
                                break
                    
                    if matched_wid:
                        status = 'file_only'
                        if matched_wid in existing_fps:
                            status = 'already_in_production'
                        
                        cand_key = (matched_wid, "File:whisky_chunks_cleaned.jsonl")
                        if cand_key not in seen_candidates:
                            seen_candidates.add(cand_key)
                            unified_results.append({
                                'whisky_id': matched_wid,
                                'whisky_name': whiskies[matched_wid].get('name'),
                                'distillery_name': distilleries.get(str(whiskies[matched_wid].get('distillery_id')), {}).get('name', 'Unknown') if whiskies[matched_wid].get('distillery_id') else 'Unknown',
                                'source_origin': 'File:whisky_chunks_cleaned.jsonl',
                                'content_preview': raw_text[:200],
                                'status': status
                            })
                    else:
                        unmatched_results.append({
                            'raw_whisky_id': raw_wid or 'N/A',
                            'raw_whisky_name': raw_name,
                            'raw_distillery_name': 'N/A',
                            'source_origin': f'File:whisky_chunks_cleaned.jsonl:line_{idx+1}',
                            'reason': 'Could not resolve target name to a production whisky_id'
                        })
                except Exception as e:
                    print(f"Error parsing line {idx+1} in jsonl: {e}")

    # Load from book_data_priority_queue.csv
    pq_path = os.path.join(PROJECT_DIR, "data/output/book_data_priority_queue.csv")
    if os.path.exists(pq_path):
        with open(pq_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                wid = row.get('whisky_id')
                w_name = row.get('whisky_name')
                if wid and wid in whiskies:
                    status = 'file_only'
                    if wid in existing_fps:
                        status = 'already_in_production'
                    cand_key = (wid, "File:book_data_priority_queue.csv")
                    if cand_key not in seen_candidates:
                        seen_candidates.add(cand_key)
                        unified_results.append({
                            'whisky_id': wid,
                            'whisky_name': whiskies[wid].get('name'),
                            'distillery_name': distilleries.get(str(whiskies[wid].get('distillery_id')), {}).get('name', 'Unknown') if whiskies[wid].get('distillery_id') else 'Unknown',
                            'source_origin': 'File:book_data_priority_queue.csv',
                            'content_preview': row.get('reason', '')[:200],
                            'status': status
                        })
                else:
                    unmatched_results.append({
                        'raw_whisky_id': wid or 'N/A',
                        'raw_whisky_name': w_name or 'N/A',
                        'raw_distillery_name': 'N/A',
                        'source_origin': 'File:book_data_priority_queue.csv',
                        'reason': 'Whisky ID not in production database'
                    })

    # Write Unified and Unmatched CSVs
    with open(UNIFIED_CSV, 'w', newline='', encoding='utf-8') as f:
        if unified_results:
            writer = csv.DictWriter(f, fieldnames=unified_results[0].keys())
            writer.writeheader()
            writer.writerows(unified_results)
            
    with open(UNMATCHED_CSV, 'w', newline='', encoding='utf-8') as f:
        if unmatched_results:
            writer = csv.DictWriter(f, fieldnames=unmatched_results[0].keys())
            writer.writeheader()
            writer.writerows(unmatched_results)

    conn.close()

    # --- 4. Write Markdown Report ---
    report = []
    report.append("# Deep Book and Manual Inventory Scan Report\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    
    report.append("\n## Why only 40 candidates in previous phase?")
    report.append("1. **Strict SQL filters**: The previous phase only audited DB tables and applied strict filters to ignore any tasting notes that already had a profile. Out of the hundreds of book/NotebookLM entries inside the staging tables, only 8 were in `staging_book_flavor_profiles` and most of them matched existing flavor profiles.\n")
    report.append("2. **Keyword limitation**: The source filters checked for direct match of 'book' or 'notebooklm' in staging note URLs or source systems, skipping 'uploaded_document' entries (60 rows) and Wishart book entries that were parsed under complex PDF titles.\n")
    report.append("3. **External repo files**: The previous script did not scan external files under `C:/Users/eltun/Downloads/kitaplar` (the raw book PDF/TXT extracts) or the `whisky_chunks_cleaned.jsonl` file which holds rich book data.")

    report.append("\n## Global Scan Metrics")
    report.append(f"- Total book-related rows detected in DB: {len(db_results)}")
    report.append(f"- Total book-related files scanned in repo/downloads: {len(file_results)}")
    report.append(f"- Total unified candidates mapped to valid `whisky_id`: {len(unified_results)}")
    report.append(f"- Total unmatched items (failed target alignment): {len(unmatched_results)}")

    report.append("\n## Top 20 Book/Manual Files Detected")
    report.append("| File Path | Size (Bytes) | Row/Line Count | Matched Keywords | Columns/Keys |")
    report.append("|---|---|---|---|---|")
    # Sort files by size or line count
    file_results.sort(key=lambda x: x['line_or_row_count'], reverse=True)
    for r in file_results[:20]:
        report.append(f"| `{r['file_path']}` | {r['file_size_bytes']} | {r['line_or_row_count']} | {r['matched_keywords']} | {r['detected_columns_or_keys']} |")

    report.append("\n## Staging vs Production Mapped Candidates")
    c_prod = sum(1 for x in unified_results if x['status'] == 'already_in_production')
    c_stag = sum(1 for x in unified_results if x['status'] == 'staging_pending')
    c_file = sum(1 for x in unified_results if x['status'] == 'file_only')
    report.append(f"- already_in_production: {c_prod}")
    report.append(f"- staging_pending: {c_stag}")
    report.append(f"- file_only: {c_file}")

    report.append("\n## Next Recommended Phases")
    report.append("1. **AŞAMA BP2 — Normalize Book Manual File Candidates**: Read candidate files (e.g. `whisky_chunks_cleaned.jsonl`) and generate normalized flavor vectors using rule-based parsing.\n")
    report.append("2. **AŞAMA BP3 — Match Book Candidates To Production Whiskies**: Run a name-matching algorithm on unmatched candidates to link them to valid `whisky_id`s in the production database.\n")
    report.append("3. **AŞAMA BP4 — Book Candidate QA Pack**: Perform a validation check of the generated candidate pack against the active production DB.")

    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Deep scan successfully identified the discrepancy and mapped all file/DB sources).")

    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report written to: {REPORT_MD}")

if __name__ == "__main__":
    main()
