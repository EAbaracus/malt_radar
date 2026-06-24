import argparse
import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


SOURCE_SYSTEM = "structured_whisky_source_01"


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def table_info(conn, table):
    return conn.execute(f"PRAGMA table_info({table})").fetchall()


def table_columns(conn, table):
    return [r[1] for r in table_info(conn, table)]


def count_table(conn, table):
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def whisky_exists(conn, whisky_id):
    return conn.execute(
        "SELECT 1 FROM whiskies WHERE whisky_id = ? LIMIT 1",
        (whisky_id,),
    ).fetchone() is not None


def duplicate_exists(conn, row, cols):
    clauses = []
    params = []

    if "whisky_id" in cols:
        clauses.append("whisky_id = ?")
        params.append(row["whisky_id"])

    if "source_system" in cols:
        clauses.append("source_system = ?")
        params.append(row["source_system"])

    if "source_id" in cols and row.get("source_id"):
        clauses.append("source_id = ?")
        params.append(row["source_id"])

    if "source_url" in cols and row.get("source_path"):
        clauses.append("source_url = ?")
        params.append("external://structured_whisky_source_01/" + row["source_path"].replace("\\", "/"))

    if len(clauses) < 2:
        return False

    sql = "SELECT 1 FROM staging_tasting_notes WHERE " + " AND ".join(clauses) + " LIMIT 1"
    return conn.execute(sql, params).fetchone() is not None


def build_insert_row(row, cols):
    source_url = "external://structured_whisky_source_01/" + row.get("source_path", "").replace("\\", "/")
    created = now_iso()

    candidates = {
        "whisky_id": row.get("whisky_id", ""),
        "source_system": row.get("source_system", SOURCE_SYSTEM),
        "source_id": row.get("source_id", ""),
        "source_url": source_url,
        "source_name": row.get("source_name", ""),
        "source_title": row.get("source_name", ""),
        "source_product_name": row.get("source_name", ""),
        "matched_whisky_name": row.get("matched_whisky_name", ""),
        "note_text": row.get("note_text", ""),
        "raw_note_text": row.get("note_text", ""),
        "notes": row.get("note_text", ""),
        "tasting_note": row.get("note_text", ""),
        "note_language": row.get("note_language", "en"),
        "language": row.get("note_language", "en"),
        "note_type": row.get("note_type", "external_structured_preview"),
        "approval_status": row.get("approval_status", "staging_pending_review"),
        "import_status": "staging_pending_review",
        "match_status": row.get("match_status", ""),
        "match_score": row.get("match_score", ""),
        "source_abv": row.get("source_abv", ""),
        "source_age": row.get("source_age", ""),
        "source_bottler": row.get("source_bottler", ""),
        "source_external_ids": row.get("source_external_ids", ""),
        "created_at": created,
        "updated_at": created,
        "inserted_at": created,
    }

    insert_row = {}
    for col in cols:
        if col in candidates and candidates[col] != "":
            insert_row[col] = candidates[col]

    return insert_row


def validate_required_columns(conn, insert_row):
    problems = []
    for cid, name, coltype, notnull, default, pk in table_info(conn, "staging_tasting_notes"):
        if pk:
            continue
        if notnull and default is None and name not in insert_row:
            problems.append(name)
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    input_path = Path(args.input)
    db_path = Path(args.db)
    report_path = Path(args.report)

    rows = read_csv(input_path)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    cols = table_columns(conn, "staging_tasting_notes")
    before = count_table(conn, "staging_tasting_notes")

    inserted = 0
    blocked = []

    try:
        for row in rows:
            if row.get("match_status") != "high":
                blocked.append({**row, "block_reason": "not_high_match"})
                continue

            if not whisky_exists(conn, row.get("whisky_id", "")):
                blocked.append({**row, "block_reason": "missing_fk_whisky_id"})
                continue

            if not row.get("note_text", "").strip():
                blocked.append({**row, "block_reason": "empty_note_text"})
                continue

            if duplicate_exists(conn, row, cols):
                blocked.append({**row, "block_reason": "duplicate_staging_tasting_note"})
                continue

            insert_row = build_insert_row(row, cols)
            missing_required = validate_required_columns(conn, insert_row)
            if missing_required:
                blocked.append({**row, "block_reason": "missing_required_columns:" + ",".join(missing_required)})
                continue

            keys = list(insert_row.keys())
            placeholders = ", ".join(["?"] * len(keys))
            sql = f"INSERT INTO staging_tasting_notes ({', '.join(keys)}) VALUES ({placeholders})"
            conn.execute(sql, [insert_row[k] for k in keys])
            inserted += 1

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        after = count_table(conn, "staging_tasting_notes")
        conn.close()

    blocked_path = Path("data/output/structured_whisky_source_01_staging_apply_blocked.csv")
    blocked_path.parent.mkdir(parents=True, exist_ok=True)
    if blocked:
        fieldnames = sorted({k for r in blocked for k in r.keys()})
        with blocked_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(blocked)

    lines = []
    lines.append("# Structured Whisky Source 01 High-safe Staging Apply")
    lines.append("")
    lines.append(f"- Input: `{input_path}`")
    lines.append(f"- DB: `{db_path}`")
    lines.append(f"- staging_tasting_notes before: {before}")
    lines.append(f"- inserted: {inserted}")
    lines.append(f"- blocked: {len(blocked)}")
    lines.append(f"- staging_tasting_notes after: {after}")
    lines.append("")
    lines.append("## Gate")
    lines.append("")
    if inserted > 0 and len(blocked) == 0 and after == before + inserted:
        lines.append("- Gate: **GO_APPLIED_TO_STAGING**")
    elif inserted > 0:
        lines.append("- Gate: **PARTIAL_APPLY_REVIEW_BLOCKED**")
    else:
        lines.append("- Gate: **NO-GO**")
    lines.append("")
    lines.append("## Safety")
    lines.append("")
    lines.append("- production tasting_notes table write: **NO**")
    lines.append("- flavor_profiles table write: **NO**")
    lines.append("- only staging_tasting_notes write attempted")
    lines.append("- source_system: `structured_whisky_source_01`")
    lines.append("")
    if blocked:
        lines.append(f"Blocked CSV: `{blocked_path}`")
        lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"inserted: {inserted}")
    print(f"blocked: {len(blocked)}")
    print(f"wrote: {report_path}")


if __name__ == "__main__":
    main()

