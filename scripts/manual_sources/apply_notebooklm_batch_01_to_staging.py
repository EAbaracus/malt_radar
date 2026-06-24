import argparse
import csv
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def read_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--preview-csv", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    db_path = Path(args.db)
    preview_path = Path(args.preview_csv)
    report_path = Path(args.report)

    if not db_path.exists():
        raise FileNotFoundError(db_path)
    if not preview_path.exists():
        raise FileNotFoundError(preview_path)

    backup_path = db_path.with_name("production_before_notebooklm_batch_01_staging.db")
    shutil.copy2(db_path, backup_path)

    rows = read_csv(preview_path)

    now = datetime.now(timezone.utc).isoformat()

    eligible = []
    blocked = []

    for row in rows:
        confidence = (row.get("confidence") or "").strip().lower()
        whisky_id = (row.get("whisky_id") or "").strip()

        if not whisky_id:
            blocked.append((row.get("source_whisky_name"), "missing_whisky_id"))
            continue

        if confidence != "high":
            blocked.append((row.get("source_whisky_name"), f"not_high_confidence:{confidence}"))
            continue

        eligible.append(row)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS staging_notebooklm_flavor_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            whisky_id TEXT NOT NULL,
            whisky_name TEXT,
            source_whisky_name TEXT,
            source_system TEXT NOT NULL,
            source_hint TEXT,
            confidence TEXT,
            match_score REAL,
            match_name_score REAL,
            match_distillery_score REAL,
            nose_summary TEXT,
            palate_summary TEXT,
            finish_summary TEXT,
            flavour_tags TEXT,
            smoky REAL,
            sherry REAL,
            fruity REAL,
            sweet REAL,
            spicy REAL,
            oaky REAL,
            maritime REAL,
            approval_status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(whisky_id, source_system)
        )
    """)

    inserted = 0
    duplicate = 0

    for row in eligible:
        try:
            cur.execute("""
                INSERT INTO staging_notebooklm_flavor_profiles (
                    whisky_id,
                    whisky_name,
                    source_whisky_name,
                    source_system,
                    source_hint,
                    confidence,
                    match_score,
                    match_name_score,
                    match_distillery_score,
                    nose_summary,
                    palate_summary,
                    finish_summary,
                    flavour_tags,
                    smoky,
                    sherry,
                    fruity,
                    sweet,
                    spicy,
                    oaky,
                    maritime,
                    approval_status,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row.get("whisky_id"),
                row.get("whisky_name"),
                row.get("source_whisky_name"),
                row.get("source_system") or "notebooklm_book_profile",
                row.get("source_hint"),
                row.get("confidence"),
                float(row["match_score"]) if row.get("match_score") else None,
                float(row["match_name_score"]) if row.get("match_name_score") else None,
                float(row["match_distillery_score"]) if row.get("match_distillery_score") else None,
                row.get("nose_summary"),
                row.get("palate_summary"),
                row.get("finish_summary"),
                row.get("flavour_tags"),
                float(row["smoky"]) if row.get("smoky") else None,
                float(row["sherry"]) if row.get("sherry") else None,
                float(row["fruity"]) if row.get("fruity") else None,
                float(row["sweet"]) if row.get("sweet") else None,
                float(row["spicy"]) if row.get("spicy") else None,
                float(row["oaky"]) if row.get("oaky") else None,
                float(row["maritime"]) if row.get("maritime") else None,
                row.get("approval_status") or "staging_pending_review",
                now,
            ))
            inserted += 1
        except sqlite3.IntegrityError:
            duplicate += 1

    conn.commit()

    total_staging = cur.execute("""
        SELECT COUNT(*)
        FROM staging_notebooklm_flavor_profiles
    """).fetchone()[0]

    pending = cur.execute("""
        SELECT COUNT(*)
        FROM staging_notebooklm_flavor_profiles
        WHERE approval_status = 'staging_pending_review'
    """).fetchone()[0]

    fk_missing = cur.execute("""
        SELECT COUNT(*)
        FROM staging_notebooklm_flavor_profiles s
        LEFT JOIN whiskies w ON w.whisky_id = s.whisky_id
        WHERE w.whisky_id IS NULL
    """).fetchone()[0]

    conn.close()

    report = []
    report.append("# NotebookLM Batch 01 Staging Apply Report")
    report.append("")
    report.append(f"- DB: `{db_path}`")
    report.append(f"- Backup: `{backup_path}`")
    report.append(f"- Preview CSV: `{preview_path}`")
    report.append(f"- Preview rows: {len(rows)}")
    report.append(f"- Eligible high-confidence rows: {len(eligible)}")
    report.append(f"- Inserted: {inserted}")
    report.append(f"- Duplicate skipped: {duplicate}")
    report.append(f"- Blocked/review kept out: {len(blocked)}")
    report.append(f"- Total staging_notebooklm_flavor_profiles: {total_staging}")
    report.append(f"- Pending review: {pending}")
    report.append(f"- FK missing: {fk_missing}")
    report.append("")
    report.append("## Inserted Candidates")
    for row in eligible:
        report.append(f"- {row.get('whisky_id')} | {row.get('whisky_name')} | source={row.get('source_whisky_name')} | confidence={row.get('confidence')} | score={row.get('match_score')}")
    report.append("")
    report.append("## Blocked / Review Kept Out")
    for name, reason in blocked:
        report.append(f"- {name} | {reason}")
    report.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report), encoding="utf-8")

    print(f"backup={backup_path}")
    print(f"preview_rows={len(rows)}")
    print(f"eligible_high_confidence={len(eligible)}")
    print(f"inserted={inserted}")
    print(f"duplicate_skipped={duplicate}")
    print(f"blocked_or_review={len(blocked)}")
    print(f"total_staging={total_staging}")
    print(f"fk_missing={fk_missing}")
    print(f"report={report_path}")


if __name__ == "__main__":
    main()
