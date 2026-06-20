import sqlite3

conn = sqlite3.connect("output/import/production.db")

checks = {
    "whiskies": "SELECT COUNT(*) FROM whiskies",
    "flavor_profiles": "SELECT COUNT(*) FROM flavor_profiles",
    "whiskeymapper_profiles": "SELECT COUNT(*) FROM flavor_profiles WHERE flavor_source='whiskeymapper'",
    "tasting_notes": "SELECT COUNT(*) FROM tasting_notes",
    "staging_tasting_notes": "SELECT COUNT(*) FROM staging_tasting_notes",
    "fk_missing": """
        SELECT COUNT(*)
        FROM flavor_profiles fp
        LEFT JOIN whiskies w ON w.whisky_id = fp.whisky_id
        WHERE w.whisky_id IS NULL
    """,
    "duplicate_profiles": """
        SELECT COUNT(*)
        FROM (
            SELECT whisky_id, COUNT(*) c
            FROM flavor_profiles
            GROUP BY whisky_id
            HAVING c > 1
        )
    """,
}

for label, sql in checks.items():
    value = conn.execute(sql).fetchone()[0]
    print(f"{label}: {value}")

conn.close()
