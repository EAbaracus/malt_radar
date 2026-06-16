import sqlite3
import argparse
import json
import os

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def inspect_db(db_path):
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    report = {}

    # 1. Table row counts
    tables = [
        "countries", "regions", "distilleries", "independent_bottlers",
        "whisky_products", "cask_types", "product_cask_types",
        "flavor_tags", "product_flavor_tags", "source_audit",
        "entity_sources", "rejected_matches", "review_needed"
    ]
    report["table_counts"] = {}
    for t in tables:
        try:
            cursor.execute(f"SELECT count(*) as c FROM {t}")
            report["table_counts"][t] = cursor.fetchone()['c']
        except sqlite3.OperationalError:
            report["table_counts"][t] = "Table not found"

    # 2. PRAGMA foreign_key_check
    cursor.execute("PRAGMA foreign_key_check;")
    fk_errors = cursor.fetchall()
    report["foreign_key_violations"] = fk_errors

    # 3. review_needed top 20
    cursor.execute("SELECT * FROM review_needed LIMIT 20")
    report["review_needed_top_20"] = cursor.fetchall()

    # 4. rejected_matches top 20
    cursor.execute("SELECT * FROM rejected_matches LIMIT 20")
    report["rejected_matches_top_20"] = cursor.fetchall()

    # 5. low confidence products
    cursor.execute("SELECT id, name, confidence_score FROM whisky_products WHERE confidence_score = 'low'")
    report["low_confidence_products"] = cursor.fetchall()

    # 6. products without source_url
    cursor.execute("""
        SELECT p.id, p.name 
        FROM whisky_products p 
        LEFT JOIN entity_sources es ON p.id = es.entity_id AND es.entity_type = 'whisky_product'
        WHERE es.id IS NULL
    """)
    report["products_without_source_urls"] = cursor.fetchall()

    # 7. Independent product missing bottler_id
    cursor.execute("""
        SELECT id, name FROM whisky_products 
        WHERE bottling_type = 'independent' AND bottler_id IS NULL
    """)
    report["independent_missing_bottler"] = cursor.fetchall()

    # 8. Official product having bottler_id
    cursor.execute("""
        SELECT id, name, bottler_id FROM whisky_products 
        WHERE bottling_type = 'official' AND bottler_id IS NOT NULL
    """)
    report["official_has_bottler"] = cursor.fetchall()

    # 9. Cask and flavor tag fill rates
    total_products = report["table_counts"].get("whisky_products", 0)
    
    if total_products > 0:
        cursor.execute("SELECT count(DISTINCT product_id) as c FROM product_cask_types")
        cask_filled = cursor.fetchone()['c']
        report["cask_fill_rate_percentage"] = round((cask_filled / total_products) * 100, 2)
        
        cursor.execute("SELECT count(DISTINCT product_id) as c FROM product_flavor_tags")
        flavor_filled = cursor.fetchone()['c']
        report["flavor_fill_rate_percentage"] = round((flavor_filled / total_products) * 100, 2)
    else:
        report["cask_fill_rate_percentage"] = 0
        report["flavor_fill_rate_percentage"] = 0

    conn.close()

    # Print to console
    print("\n" + "="*50)
    print("WHISKY DATABASE INSPECTION REPORT")
    print("="*50)
    
    print("\n1. TABLE COUNTS:")
    for t, c in report["table_counts"].items():
        print(f"  - {t}: {c}")

    print(f"\n2. FK VIOLATIONS: {len(report['foreign_key_violations'])}")
    
    print(f"\n3. REVIEW NEEDED (Top 20): {len(report['review_needed_top_20'])} records shown")
    print(f"4. REJECTED MATCHES (Top 20): {len(report['rejected_matches_top_20'])} records shown")
    print(f"5. LOW CONFIDENCE PRODUCTS: {len(report['low_confidence_products'])}")
    print(f"6. PRODUCTS WITHOUT SOURCE URLs: {len(report['products_without_source_urls'])}")
    print(f"7. INDEPENDENT WITH NO BOTTLER ID: {len(report['independent_missing_bottler'])}")
    print(f"8. OFFICIAL WITH BOTTLER ID: {len(report['official_has_bottler'])}")
    
    print(f"\n9. DATA FILL RATES:")
    print(f"  - Cask Types: {report['cask_fill_rate_percentage']}%")
    print(f"  - Flavor Tags: {report['flavor_fill_rate_percentage']}%")
    print("="*50 + "\n")

    # Output JSON
    output_dir = os.path.dirname(db_path)
    report_path = os.path.join(output_dir, 'inspection_report.json')
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4, ensure_ascii=False)
        
    print(f"Detailed JSON report written to: {report_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Inspect Whisky DB')
    parser.add_argument('--db', required=True, help='Path to SQLite database')
    args = parser.parse_args()
    
    inspect_db(args.db)
