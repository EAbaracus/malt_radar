import argparse
import csv
import json
import sqlite3
from pathlib import Path


BLOCKED_TYPES = {
    "Cream Liqueur",
}


def load_jsonl(path):
    rows = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def existing_profile_whisky_ids(db_path):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    ids = {
        row[0]
        for row in cur.execute("""
            SELECT DISTINCT whisky_id
            FROM flavor_profiles
            WHERE whisky_id IS NOT NULL
        """)
    }
    conn.close()
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean-jsonl", required=True)
    ap.add_argument("--match-csv", required=True)
    ap.add_argument("--db", required=True)
    ap.add_argument("--output-jsonl", required=True)
    ap.add_argument("--output-csv", required=True)
    ap.add_argument("--report", required=True)
    args = ap.parse_args()

    source_rows = load_jsonl(args.clean_jsonl)
    match_rows = load_csv(args.match_csv)
    existing_profiles = existing_profile_whisky_ids(args.db)

    source_by_name = {
        (r.get("whisky_name") or "").strip().lower(): r
        for r in source_rows
    }

    preview = []
    blocked = []
    review = []

    seen_whisky_ids = set()

    for m in match_rows:
        source_name = (m.get("source_whisky_name") or "").strip()
        src = source_by_name.get(source_name.lower())

        if not src:
            blocked.append((source_name, "source_not_found"))
            continue

        whisky_id = m.get("matched_whisky_id")
        match_gate = m.get("match_gate")
        source_type = src.get("type")
        source_confidence = src.get("confidence")

        if source_type in BLOCKED_TYPES:
            blocked.append((source_name, "blocked_type"))
            continue

        if match_gate == "REVIEW":
            review.append((source_name, "match_review"))
            continue

        if match_gate != "HIGH":
            blocked.append((source_name, "not_high_match"))
            continue

        if source_confidence == "low":
            review.append((source_name, "low_source_confidence"))
            continue

        if not whisky_id:
            blocked.append((source_name, "missing_matched_whisky_id"))
            continue

        if whisky_id in existing_profiles:
            blocked.append((source_name, "already_has_flavor_profile"))
            continue

        if whisky_id in seen_whisky_ids:
            blocked.append((source_name, "duplicate_matched_whisky_id_in_batch"))
            continue

        seen_whisky_ids.add(whisky_id)

        row = {
            "whisky_id": whisky_id,
            "whisky_name": m.get("matched_whisky_name"),
            "source_whisky_name": source_name,
            "source_system": "notebooklm_book_profile",
            "source_hint": src.get("source_hint"),
            "confidence": source_confidence,
            "match_score": m.get("score"),
            "match_name_score": m.get("name_score"),
            "match_distillery_score": m.get("distillery_score"),
            "nose_summary": src.get("nose_summary"),
            "palate_summary": src.get("palate_summary"),
            "finish_summary": src.get("finish_summary"),
            "flavour_tags": src.get("flavour_tags") or [],
            "smoky": (src.get("radar_signals") or {}).get("smoky"),
            "sherry": (src.get("radar_signals") or {}).get("sherry"),
            "fruity": (src.get("radar_signals") or {}).get("fruity"),
            "sweet": (src.get("radar_signals") or {}).get("sweet"),
            "spicy": (src.get("radar_signals") or {}).get("spicy"),
            "oaky": (src.get("radar_signals") or {}).get("oaky"),
            "maritime": (src.get("radar_signals") or {}).get("maritime"),
            "approval_status": "staging_pending_review",
        }
        preview.append(row)

    out_jsonl = Path(args.output_jsonl)
    out_csv = Path(args.output_csv)
    report_path = Path(args.report)

    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with out_jsonl.open("w", encoding="utf-8", newline="\n") as f:
        for row in preview:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    fieldnames = [
        "whisky_id", "whisky_name", "source_whisky_name",
        "source_system", "source_hint", "confidence",
        "match_score", "match_name_score", "match_distillery_score",
        "nose_summary", "palate_summary", "finish_summary",
        "flavour_tags",
        "smoky", "sherry", "fruity", "sweet", "spicy", "oaky", "maritime",
        "approval_status",
    ]

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in preview:
            r = dict(row)
            r["flavour_tags"] = "|".join(r.get("flavour_tags") or [])
            w.writerow(r)

    report = []
    report.append("# NotebookLM Staging Preview Report")
    report.append("")
    report.append(f"- Source rows: {len(source_rows)}")
    report.append(f"- Match rows: {len(match_rows)}")
    report.append(f"- Existing flavor profile whisky_ids: {len(existing_profiles)}")
    report.append(f"- Staging preview rows: {len(preview)}")
    report.append(f"- Review rows: {len(review)}")
    report.append(f"- Blocked rows: {len(blocked)}")
    report.append("")
    report.append("## Preview Rows")
    for row in preview[:100]:
        report.append(f"- {row['whisky_id']} | {row['whisky_name']} | source={row['source_whisky_name']} | confidence={row['confidence']}")
    report.append("")
    report.append("## Review Rows")
    for name, reason in review[:100]:
        report.append(f"- {name} | {reason}")
    report.append("")
    report.append("## Blocked Rows")
    for name, reason in blocked[:150]:
        report.append(f"- {name} | {reason}")
    report.append("")

    report_path.write_text("\n".join(report), encoding="utf-8")

    print(f"source_rows={len(source_rows)}")
    print(f"match_rows={len(match_rows)}")
    print(f"existing_profiles={len(existing_profiles)}")
    print(f"staging_preview_rows={len(preview)}")
    print(f"review_rows={len(review)}")
    print(f"blocked_rows={len(blocked)}")
    print(f"output_jsonl={out_jsonl}")
    print(f"output_csv={out_csv}")
    print(f"report={report_path}")


if __name__ == "__main__":
    main()