"""Merge all per-source editorial staging DBs into one unified staging DB.

Read-only w.r.t. production; writes ONLY output/staging/unified_staging.db.
Idempotent: re-running rebuilds the unified DB from the per-source DBs.

Usage:
    python mr-kep/editorial/scripts/merge_staging_dbs.py [--out PATH]

Source DBs (each created by crawl_fici_theviskici.py --staging ...):
    output/staging/fici_theviskici_staging.db   (ficisertligi + theviskici)
    output/staging/fici_re_staging.db           (ficisertligi re-crawl, fix sonrası)
    output/staging/viskibilgi_staging.db
    output/staging/greatdrams_staging.db
    output/staging/rumhowler_staging.db
    output/staging/scotchnoob_staging.db
    output/staging/bourbonculture_staging.db
    output/staging/whiskysaga_staging.db
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # repo root
sys.path.insert(0, str(ROOT / "mr-kep"))

DDL = (ROOT / "mr-kep/editorial/schema/staging_editorial.ddl.sql").read_text(
    encoding="utf-8", errors="replace"
)

SOURCES = [
    ("ficisertligi", ROOT / "output/staging/fici_re_staging.db", None),
    # fici_theviskici_staging.db holds BOTH sources; take only theviskici rows
    # so the ficisertligi rows above (fixed re-crawl) are not overwritten.
    ("theviskici", ROOT / "output/staging/fici_theviskici_staging.db", "theviskici"),
    ("viskibilgi", ROOT / "output/staging/viskibilgi_staging.db", None),
    ("greatdrams", ROOT / "output/staging/greatdrams_staging.db", None),
    ("rumhowler", ROOT / "output/staging/rumhowler_re_staging.db", None),
    ("scotchnoob", ROOT / "output/staging/scotchnoob_staging.db", None),
    ("bourbonculture", ROOT / "output/staging/bourbonculture_staging.db", None),
    ("whiskysaga", ROOT / "output/staging/whiskysaga_staging.db", None),
]

COLUMNS = [
    "evidence_id", "source_id", "source_url", "authority_tier", "author",
    "published_date", "content_hash", "raw_name", "normalized_name",
    "matched_master_whisky_id", "match_status", "match_confidence",
    "score_value", "score_scale_max", "score_normalized",
    "nose", "palate", "finish", "conclusion", "flavor_vector_json",
    "metadata_json", "evidence_confidence", "extraction_method",
    "provenance_state",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "output/staging/unified_staging.db"))
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()

    conn = sqlite3.connect(str(out))
    conn.executescript(DDL)

    total = 0
    per_source = {}
    dupes = 0
    for source_id, db_path, source_filter in SOURCES:
        if not db_path.exists():
            print(f"[skip] {source_id}: {db_path.name} yok")
            continue
        src = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        if source_filter:
            rows = src.execute(
                f"SELECT {', '.join(COLUMNS)} FROM staging_editorial_reviews "
                f"WHERE source_id = ?", (source_filter,)
            ).fetchall()
        else:
            rows = src.execute(
                f"SELECT {', '.join(COLUMNS)} FROM staging_editorial_reviews"
            ).fetchall()
        src.close()
        n = 0
        for row in rows:
            # evidence_id deterministik: source_id|source_url SHA. Tablo
            # kaynak DB'de zaten bu şekilde üretildi; yine de garanti.
            try:
                conn.execute(
                    f"INSERT OR REPLACE INTO staging_editorial_reviews "
                    f"({', '.join(COLUMNS)}) VALUES ({', '.join('?' * len(COLUMNS))})",
                    row,
                )
                n += 1
            except sqlite3.IntegrityError:
                dupes += 1
        total += n
        per_source[source_id] = n
        print(f"[ok] {source_id}: {n} rows")

    conn.commit()
    conn.close()

    print(f"\nUNIFIED: {total} rows | {len(per_source)} sources | dupes={dupes}")
    for k, v in sorted(per_source.items(), key=lambda x: -x[1]):
        print(f"  {k:16s} {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
