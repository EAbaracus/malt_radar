import sqlite3
from pathlib import Path

DB_PATH = Path("output/import/production.db")

def table_exists(cur, table_name):
    row = cur.execute(
        "SELECT COUNT(*) AS c FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row["c"] > 0

def get_columns(cur, table_name):
    rows = cur.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row["name"] for row in rows]

def safe_count(cur, table_name):
    if not table_exists(cur, table_name):
        return None
    return cur.execute(f"SELECT COUNT(*) AS c FROM {table_name}").fetchone()["c"]

def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"DB not found: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print("REAL DB SCHEMA AUDIT")
    print("====================")
    print()

    tables = cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()

    print("TABLES:")
    for t in tables:
        print("-", t["name"])

    print()
    print("CORE TABLE COUNTS")
    print("-----------------")

    for table_name in [
        "whiskies",
        "flavor_profiles",
        "tasting_notes",
        "staging_tasting_notes",
        "staging_external_reviews",
        "staging_manual_review_queue",
    ]:
        count = safe_count(cur, table_name)
        if count is None:
            print(f"{table_name}: table not found")
        else:
            print(f"{table_name}: {count}")

    print()
    print("TABLE COLUMNS")
    print("-------------")

    for table_name in ["whiskies", "flavor_profiles", "tasting_notes", "staging_tasting_notes"]:
        if table_exists(cur, table_name):
            print()
            print(f"{table_name}:")
            for col in get_columns(cur, table_name):
                print(f"  - {col}")

    print()
    print("FLAVOR COVERAGE ESTIMATE")
    print("------------------------")

    if not table_exists(cur, "whiskies"):
        print("ERROR: whiskies table not found.")
        conn.close()
        return

    whisky_count = safe_count(cur, "whiskies") or 0

    if not table_exists(cur, "flavor_profiles"):
        print(f"Total whiskies: {whisky_count}")
        print("Whiskies with flavor profile: 0")
        print(f"Whiskies without flavor profile: {whisky_count}")
        print("Coverage: 0.00%")
        conn.close()
        return

    flavor_cols = get_columns(cur, "flavor_profiles")

    possible_fk_cols = [
        "whisky_id",
        "product_id",
        "whisky_uuid",
        "entity_id",
        "id",
    ]

    fk_col = None
    for col in possible_fk_cols:
        if col in flavor_cols:
            fk_col = col
            break

    if fk_col is None:
        print("Could not detect whisky reference column in flavor_profiles.")
        print("flavor_profiles columns:")
        for col in flavor_cols:
            print("-", col)
        conn.close()
        return

    with_flavor = cur.execute(
        f"""
        SELECT COUNT(DISTINCT {fk_col}) AS c
        FROM flavor_profiles
        WHERE {fk_col} IS NOT NULL
        """
    ).fetchone()["c"]

    without_flavor = whisky_count - with_flavor
    coverage = (with_flavor / whisky_count * 100) if whisky_count else 0

    print(f"Total whiskies: {whisky_count}")
    print(f"Whiskies with flavor profile: {with_flavor}")
    print(f"Whiskies without flavor profile: {without_flavor}")
    print(f"Coverage: {coverage:.2f}%")
    print(f"Detected flavor FK column: flavor_profiles.{fk_col}")

    print()
    print("SAMPLE FLAVOR PROFILES")
    print("----------------------")

    rows = cur.execute("SELECT * FROM flavor_profiles LIMIT 5").fetchall()
    for i, row in enumerate(rows, start=1):
        print()
        print(f"Sample #{i}")
        for key in row.keys():
            print(f"{key}: {row[key]}")

    conn.close()

if __name__ == "__main__":
    main()
