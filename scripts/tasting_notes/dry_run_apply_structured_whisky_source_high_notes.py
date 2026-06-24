import argparse
import csv
import sqlite3
from collections import Counter
from pathlib import Path


REQUIRED_COLUMNS = [
    "source_system",
    "source_path",
    "source_id",
    "whisky_id",
    "matched_whisky_name",
    "source_name",
    "match_status",
    "match_score",
    "note_language",
    "note_type",
    "approval_status",
    "note_text",
]


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def table_columns(conn, table):
    return [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def whisky_exists(conn, whisky_id):
    row = conn.execute(
        "SELECT 1 FROM whiskies WHERE whisky_id = ? LIMIT 1",
        (whisky_id,),
    ).fetchone()
    return row is not None


def duplicate_exists(conn, row):
    cols = table_columns(conn, "staging_tasting_notes")
    if not cols:
        return False

    whisky_id = row.get("whisky_id", "")
    source_system = row.get("source_system", "")
    source_id = row.get("source_id", "")
    source_path = row.get("source_path", "")

    clauses = []
    params = []

    if "whisky_id" in cols and whisky_id:
        clauses.append("whisky_id = ?")
        params.append(whisky_id)

    if "source_system" in cols and source_system:
        clauses.append("source_system = ?")
        params.append(source_system)

    if "source_id" in cols and source_id:
        clauses.append("source_id = ?")
        params.append(source_id)

    if "source_url" in cols and source_path:
        clauses.append("source_url = ?")
        params.append(source_path)

    if len(clauses) < 2:
        return False

    sql = "SELECT 1 FROM staging_tasting_notes WHERE " + " AND ".join(clauses) + " LIMIT 1"

    try:
        return conn.execute(sql, params).fetchone() is not None
    except sqlite3.OperationalError:
        return False


def validate_row(conn, row):
    missing = [c for c in REQUIRED_COLUMNS if c not in row]
    if missing:
        return False, "missing_columns:" + ",".join(missing)

    if row.get("match_status") != "high":
        return False, "not_high_match"

    if not row.get("whisky_id"):
        return False, "missing_whisky_id"

    if not whisky_exists(conn, row["whisky_id"]):
        return False, "missing_fk_whisky_id"

    if not row.get("note_text", "").strip():
        return False, "empty_note_text"

    if duplicate_exists(conn, row):
        return False, "duplicate_staging_tasting_note"

    return True, "planned"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--db", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    input_path = Path(args.input)
    db_path = Path(args.db)
    out_path = Path(args.out)
    report_path = Path(args.report)

    rows = read_csv(input_path)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    output = []
    counts = Counter()

    for row in rows:
        ok, reason = validate_row(conn, row)
        counts[reason] += 1
        output.append({
            **row,
            "dry_run_status": "planned_insert" if ok else "blocked",
            "dry_run_reason": reason,
        })

    conn.close()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(output[0].keys()) if output else ["dry_run_status", "dry_run_reason"]
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(output)

    planned = sum(1 for r in output if r["dry_run_status"] == "planned_insert")
    blocked = sum(1 for r in output if r["dry_run_status"] == "blocked")

    lines = []
    lines.append("# Structured Whisky Source 01 High-safe Staging Apply Dry-run")
    lines.append("")
    lines.append(f"- Input: `{input_path}`")
    lines.append(f"- DB: `{db_path}`")
    lines.append(f"- Output: `{out_path}`")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append(f"- input rows: {len(rows)}")
    lines.append(f"- planned_insert: {planned}")
    lines.append(f"- blocked: {blocked}")
    lines.append("")
    lines.append("## Reasons")
    lines.append("")
    for k, v in counts.most_common():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## Gate")
    lines.append("")
    if planned > 0 and blocked == 0:
        lines.append("- Gate: **GO_APPLY_STAGING_AFTER_BACKUP**")
    elif planned > 0:
        lines.append("- Gate: **REVIEW_BLOCKED_BEFORE_APPLY**")
    else:
        lines.append("- Gate: **NO-GO**")
    lines.append("- Production DB write: **NO**")
    lines.append("- staging_tasting_notes write: **NO**")
    lines.append("- This was dry-run only.")
    lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"wrote: {out_path}")
    print(f"wrote: {report_path}")


if __name__ == "__main__":
    main()

