import sqlite3
import csv
import shutil
import os
from pathlib import Path
from collections import Counter

REPO_ROOT = Path(r"C:\Users\eltun\Documents\malt radar CLEAN")
PR_DB = REPO_ROOT / "output" / "import" / "production.db"
ST_DB = REPO_ROOT / "output" / "staging" / "p50_staging.db"
REPORT_DIR = REPO_ROOT / "output" / "reports"

def main():
    conn = sqlite3.connect(PR_DB)
    c = conn.cursor()

    # ===== PHASE 1: price_history investigation =====
    print("===== PHASE 1: price_history =====")

    # Schema
    c.execute("SELECT sql FROM sqlite_master WHERE name='price_history';")
    ph_schema = c.fetchone()[0]
    print(f"Schema:\n{ph_schema}\n")

    # Row count
    c.execute("SELECT COUNT(*) FROM price_history;")
    ph_count = c.fetchone()[0]
    print(f"Row count: {ph_count}")

    # Sample rows
    c.execute("SELECT * FROM price_history LIMIT 5;")
    ph_cols = [d[0] for d in c.description]
    ph_sample = c.fetchall()
    print(f"Columns: {ph_cols}")
    for row in ph_sample:
        print(row)

    # Distinct whisky_ids referenced
    c.execute("SELECT COUNT(DISTINCT whisky_id) FROM price_history;")
    ph_distinct_whiskies = c.fetchone()[0]
    print(f"Distinct whisky_ids referenced: {ph_distinct_whiskies}")

    # Check if any price_history whisky_id is missing from whiskies
    c.execute("SELECT COUNT(*) FROM price_history ph LEFT JOIN whiskies w ON ph.whisky_id = w.whisky_id WHERE w.whisky_id IS NULL;")
    ph_orphans = c.fetchone()[0]
    print(f"Orphan price_history rows (whisky not found): {ph_orphans}")

    # All tables with FOREIGN KEY
    c.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND sql LIKE '%FOREIGN KEY%';")
    fk_tables = c.fetchall()
    print(f"\nTables with FOREIGN KEY constraints: {[t[0] for t in fk_tables]}")

    # All tables referencing price_history
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND sql LIKE '%price_history%' AND name != 'price_history';")
    ph_refs = c.fetchall()
    print(f"Tables referencing price_history: {[t[0] for t in ph_refs]}")

    # All indexes on price_history
    c.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='price_history';")
    ph_indexes = c.fetchall()
    print(f"Indexes on price_history: {ph_indexes}")

    # All triggers on price_history
    c.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND sql LIKE '%price_history%';")
    ph_triggers = c.fetchall()
    print(f"Triggers on price_history: {ph_triggers}")

    # All views referencing price_history
    c.execute("SELECT name FROM sqlite_master WHERE type='view' AND sql LIKE '%price_history%';")
    ph_views = c.fetchall()
    print(f"Views on price_history: {ph_views}")

    # ===== PHASE 2: ABV investigation =====
    print("\n===== PHASE 2: ABV investigation =====")

    # Total whiskies
    c.execute("SELECT COUNT(*) FROM whiskies;")
    total_whiskies = c.fetchone()[0]
    print(f"Total whiskies: {total_whiskies}")

    # ABV distribution
    c.execute("SELECT COUNT(*) FROM whiskies WHERE abv IS NULL;")
    abv_null = c.fetchone()[0]
    print(f"ABV NULL: {abv_null}")

    c.execute("SELECT COUNT(*) FROM whiskies WHERE abv = 0;")
    abv_zero = c.fetchone()[0]
    print(f"ABV = 0: {abv_zero}")

    c.execute("SELECT COUNT(*) FROM whiskies WHERE abv > 0 AND abv <= 100;")
    abv_valid = c.fetchone()[0]
    print(f"ABV valid (0-100]: {abv_valid}")

    c.execute("SELECT COUNT(*) FROM whiskies WHERE abv > 100;")
    abv_over100 = c.fetchone()[0]
    print(f"ABV > 100: {abv_over100}")

    c.execute("SELECT COUNT(*) FROM whiskies WHERE abv < 0;")
    abv_negative = c.fetchone()[0]
    print(f"ABV < 0: {abv_negative}")

    # Frequency of invalid ABV values (> 100)
    c.execute("SELECT abv, COUNT(*) as cnt FROM whiskies WHERE abv > 100 GROUP BY abv ORDER BY cnt DESC LIMIT 30;")
    abv_freq = c.fetchall()
    print(f"\nTop 30 invalid ABV frequencies:")
    for abv, cnt in abv_freq:
        print(f"  ABV={abv} -> count={cnt}  (divided by 100 = {abv/100.0})")

    # First 100 representative invalid records
    c.execute("SELECT whisky_id, name, abv, distillery_id FROM whiskies WHERE abv > 100 ORDER BY abv DESC LIMIT 100;")
    abv_sample = c.fetchall()
    print(f"\nFirst 100 invalid ABV records (sorted by ABV desc):")
    for row in abv_sample:
        wid, name, abv_val, did = row
        corrected = abv_val / 100.0
        print(f"  {wid} | ABV={abv_val} -> {corrected}% | {name}")

    # Classification
    c.execute("SELECT abv FROM whiskies WHERE abv > 100;")
    all_invalid = [r[0] for r in c.fetchall()]

    cat_decimal_scale = 0  # /100 gives valid range
    cat_decimal_shift = 0  # /10 gives valid range
    cat_placeholder = 0
    cat_negative = 0
    cat_unknown = 0

    for v in all_invalid:
        div100 = v / 100.0
        div10 = v / 10.0
        if 20.0 <= div100 <= 75.0:
            cat_decimal_scale += 1
        elif 20.0 <= div10 <= 75.0:
            cat_decimal_shift += 1
        elif v in (999, 9999, -1, 0):
            cat_placeholder += 1
        else:
            cat_unknown += 1

    print(f"\nClassification of {len(all_invalid)} invalid ABV values:")
    print(f"  Decimal scaling error (/100 -> valid): {cat_decimal_scale}")
    print(f"  Decimal shift error (/10 -> valid): {cat_decimal_shift}")
    print(f"  Placeholder values: {cat_placeholder}")
    print(f"  Unknown anomalies: {cat_unknown}")

    fix_rate = cat_decimal_scale / len(all_invalid) * 100.0 if all_invalid else 0
    print(f"\nEstimated automatic fix rate (decimal scaling /100): {fix_rate:.2f}%")

    # Check min/max of invalid ABV values
    c.execute("SELECT MIN(abv), MAX(abv) FROM whiskies WHERE abv > 100;")
    abv_min, abv_max = c.fetchone()
    print(f"Invalid ABV range: min={abv_min}, max={abv_max}")

    # Check if /100 always lands in whisky-plausible range
    c.execute("SELECT COUNT(*) FROM whiskies WHERE abv > 100 AND (abv / 100.0 < 20.0 OR abv / 100.0 > 75.0);")
    out_of_range_div100 = c.fetchone()[0]
    print(f"Records where ABV/100 falls outside 20-75%: {out_of_range_div100}")

    conn.close()
    print("\nDone. Data collected for reports.")

if __name__ == "__main__":
    main()
