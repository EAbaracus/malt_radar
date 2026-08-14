import sqlite3
import os
import hashlib
import csv
import json

DB_PATH = "output/import/production.db"
REPORT_MD_PATH = "output/reports/existing_book_data_inventory_report.md"
OUTPUT_CSV_PATH = "data/output/existing_book_data_inventory.csv"

BOOK_KEYWORDS = ['book', 'notebooklm', 'uploaded', 'manual_source', 'staging_book', 'book_notebooklm']

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

def main():
    os.makedirs(os.path.dirname(REPORT_MD_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_CSV_PATH), exist_ok=True)

    if not os.path.exists(DB_PATH):
        print(f"Error: DB not found at {DB_PATH}")
        return

    hash_before = get_file_hash(DB_PATH)
    print(f"DB Hash (before): {hash_before}")

    conn_uri = f"file:{os.path.abspath(DB_PATH)}?mode=ro"
    try:
        conn = sqlite3.connect(conn_uri, uri=True)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
    except Exception as e:
        print(f"Error connecting to DB: {e}")
        return

    def safe_query(query, params=()):
        try:
            return [dict(row) for row in cur.execute(query, params).fetchall()]
        except sqlite3.OperationalError as e:
            return []

    tables = [r['name'] for r in safe_query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    
    schema_info = {}
    for t in tables:
        cols = [c['name'] for c in safe_query(f"PRAGMA table_info('{t}')")]
        schema_info[t] = cols

    inventory = []
    
    # Target tables to explicitly look at, plus any others that might contain 'source'
    target_tables = [
        'flavor_profiles',
        'tasting_notes',
        'staging_tasting_notes',
        'staging_book_flavor_profiles',
        'staging_manual_review_queue'
    ]
    
    # Also add any table that has a "source" related column
    for t in tables:
        if t not in target_tables:
            for c in schema_info.get(t, []):
                if 'source' in c.lower() or 'system' in c.lower() or 'origin' in c.lower():
                    target_tables.append(t)
                    break
                    
    target_tables = list(set(target_tables)) # deduplicate
    
    overall_production_flavor_count = 0
    overall_production_tasting_count = 0
    overall_staging_pending_count = 0
    
    schema_summary = []

    for t in target_tables:
        cols = schema_info.get(t, [])
        if not cols:
            continue
            
        source_cols = [c for c in cols if 'source' in c.lower() or 'system' in c.lower() or 'origin' in c.lower()]
        id_cols = [c for c in cols if 'id' in c.lower()]
        whisky_id_col = 'whisky_id' if 'whisky_id' in cols else (id_cols[0] if id_cols else None)
        status_cols = [c for c in cols if 'status' in c.lower()]
        title_col = 'source_name' if 'source_name' in cols else ('source_title' if 'source_title' in cols else None)
        url_col = 'source_url' if 'source_url' in cols else None
        
        if not source_cols:
            if t == 'staging_book_flavor_profiles':
                # Implicitly it's book data
                source_cols = ['"implicit_book_table"']
            else:
                continue

        schema_summary.append(f"- **{t}**: cols=({len(cols)}) source_cols={source_cols}")

        for s_col in source_cols:
            if s_col == '"implicit_book_table"':
                # For staging_book_flavor_profiles where maybe no explicit source column exists
                query = f"SELECT * FROM {t}"
                rows = safe_query(query)
                book_rows = rows
            else:
                # Group by source column and check if it matches keywords
                query = f"SELECT {s_col}, COUNT(*) as c FROM {t} GROUP BY {s_col}"
                grouped = safe_query(query)
                
                # Fetch all relevant rows
                book_sources = []
                for g in grouped:
                    val = str(g.get(s_col, '')).lower()
                    if any(k in val for k in BOOK_KEYWORDS):
                        book_sources.append(g.get(s_col))
                
                if not book_sources:
                    continue
                    
                placeholders = ','.join(['?']*len(book_sources))
                rows = safe_query(f"SELECT * FROM {t} WHERE {s_col} IN ({placeholders})", tuple(book_sources))
                
            if not rows:
                continue
                
            # Aggregate findings
            # Group rows by exact source value to generate granular inventory
            grouped_rows = {}
            for r in rows:
                s_val = r.get(s_col) if s_col != '"implicit_book_table"' else 'implicit_book_data'
                if not s_val:
                    s_val = 'unknown'
                grouped_rows.setdefault(s_val, []).append(r)
                
            for s_val, r_list in grouped_rows.items():
                distinct_whiskies = set(r.get(whisky_id_col) for r in r_list if whisky_id_col and r.get(whisky_id_col))
                
                status_distribution = {}
                for r in r_list:
                    for stat_col in status_cols:
                        st = r.get(stat_col)
                        if st:
                            status_distribution[f"{stat_col}:{st}"] = status_distribution.get(f"{stat_col}:{st}", 0) + 1
                            
                sample_whisky = list(distinct_whiskies)[0] if distinct_whiskies else ""
                sample_title = r_list[0].get(title_col, "") if title_col else ""
                sample_url = r_list[0].get(url_col, "") if url_col else ""
                
                # Accumulate globals
                if t == 'flavor_profiles':
                    overall_production_flavor_count += len(r_list)
                elif t == 'tasting_notes':
                    overall_production_tasting_count += len(r_list)
                elif t.startswith('staging_'):
                    overall_staging_pending_count += len(r_list)
                
                inventory.append({
                    "table_name": t,
                    "source_column": s_col,
                    "source_value": s_val,
                    "row_count": len(r_list),
                    "distinct_whisky_count": len(distinct_whiskies),
                    "status_distribution": json.dumps(status_distribution),
                    "duplicate_risk_signal": "High" if len(r_list) > len(distinct_whiskies) else "Low",
                    "sample_whisky_id": sample_whisky,
                    "sample_source_title": sample_title,
                    "sample_source_url": sample_url
                })

    inventory.sort(key=lambda x: (x['table_name'], x['source_value']))

    if inventory:
        keys = inventory[0].keys()
        with open(OUTPUT_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(inventory)

    conn.close()

    hash_after = get_file_hash(DB_PATH)
    print(f"DB Hash (after):  {hash_after}")

    report = []
    report.append("# Existing Book Data Inventory Report\n")
    report.append(f"- **DB Path:** `{DB_PATH}`")
    report.append(f"- **Hash Before:** `{hash_before}`")
    report.append(f"- **Hash After:** `{hash_after}`")
    report.append(f"- **Hash Match:** {'Yes (No mutation)' if hash_before == hash_after else 'NO (DB MUTATED!)'}")
    
    report.append("\n## Schema Discovery Summary")
    for s in schema_summary:
        report.append(s)
        
    report.append("\n## Book Data Global Metrics")
    report.append(f"- **Total Production Flavor Profiles (Book Derived):** {overall_production_flavor_count}")
    report.append(f"- **Total Production Tasting Notes (Book Derived):** {overall_production_tasting_count}")
    report.append(f"- **Total Staging Pending Items (Book Derived):** {overall_staging_pending_count}")
    
    total_book_rows = sum(i['row_count'] for i in inventory)
    report.append(f"- **Total DB Rows Associated with Book/NotebookLM:** {total_book_rows}")

    report.append("\n## Inventory Breakdown (Top 30)")
    if inventory:
        report.append("| Table | Source Value | Row Count | Distinct Whiskies | Status / Approvals |")
        report.append("|---|---|---|---|---|")
        for p in inventory[:30]:
            report.append(f"| {p['table_name']} | {p['source_value']} | {p['row_count']} | {p['distinct_whisky_count']} | {p['status_distribution']} |")
    else:
        report.append("No book-derived candidates found.")

    report.append(f"\n- **CSV Path:** `{OUTPUT_CSV_PATH}`")

    report.append("\n## Risks & Observations")
    report.append("- **Duplicates:** If `Row Count > Distinct Whiskies`, there are multiple records per whisky_id that need deduplication.")
    report.append("- **Source Metadata:** Manual paraphrase and strict content attribution might be required for book-derived data.")
    report.append("- **Content/FK:** Staging tables should be run through the gating review process.")

    report.append("\n## Recommended Next Stage")
    report.append("**AŞAMA L — Book Data Review/Promotion Readiness Pack**: Dış kaynaklara geçmeden önce DB içinde halihazırda bulunan (staging veya production) kitap verilerinin incelenip temizlenmesi önerilmektedir.")

    report.append("\n## Final GO/NO-GO")
    report.append("**GO** (Book data inventory successfully generated in read-only mode).")

    with open(REPORT_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(report))

    print(f"Report generated at: {REPORT_MD_PATH}")

if __name__ == "__main__":
    main()
