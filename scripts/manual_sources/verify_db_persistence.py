import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "output" / "import" / "production.db"

print("repo_root:", REPO_ROOT)
print("db_path_absolute:", DB_PATH)
print("db_exists:", DB_PATH.exists())

conn=sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
cur=conn.cursor()

for t in ["whiskies","distilleries","flavor_profiles","tasting_notes","staging_tasting_notes"]:
    try:
        count = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(t, count)
    except:
        print(t, "NOT FOUND")

exists = cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name='staging_book_flavor_profiles'"
).fetchone()
print("staging_book_flavor_profiles_exists", bool(exists))

if exists:
    print("staging_book_flavor_profiles", cur.execute("SELECT COUNT(*) FROM staging_book_flavor_profiles").fetchone()[0])
    for r in cur.execute("""
        SELECT whisky_id, whisky_name, source_book, approval_status
        FROM staging_book_flavor_profiles
        ORDER BY staging_id
    """):
        print(r)

conn.close()
