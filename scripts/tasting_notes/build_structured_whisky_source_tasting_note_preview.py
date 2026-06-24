import argparse
import csv
import json
from pathlib import Path


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def safe_json_loads(value):
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return value


def compact_text(value):
    value = safe_json_loads(value)
    if value is None:
        return ""
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.extend(str(v) for v in item.values() if v not in [None, ""])
            else:
                parts.append(str(item))
        return " | ".join(p.strip() for p in parts if p and str(p).strip())
    if isinstance(value, dict):
        return " | ".join(str(v).strip() for v in value.values() if v not in [None, ""] and str(v).strip())
    return str(value).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--entities-dir", required=True)
    parser.add_argument("--matches", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    entities_dir = Path(args.entities_dir)
    matches_path = Path(args.matches)
    out_path = Path(args.out)
    report_path = Path(args.report)

    bottlings = read_csv(entities_dir / "bottlings.csv")
    matches = read_csv(matches_path)

    by_source_path = {r["source_path"]: r for r in bottlings}

    allowed_status = {"high", "review", "manual"}
    rows = []
    blocked = []

    for m in matches:
        status = m.get("match_status", "")
        if status not in allowed_status:
            blocked.append({**m, "block_reason": "match_status_not_allowed"})
            continue

        source_path = m.get("source_path", "")
        b = by_source_path.get(source_path)
        if not b:
            blocked.append({**m, "block_reason": "missing_bottling_source"})
            continue

        official = compact_text(b.get("notes_official", ""))
        independent = compact_text(b.get("notes_independent", ""))
        description = compact_text(b.get("description", ""))

        note_text_parts = []
        if official:
            note_text_parts.append(f"Official: {official}")
        if independent:
            note_text_parts.append(f"Independent: {independent}")
        if description:
            note_text_parts.append(f"Description: {description}")

        note_text = "\n".join(note_text_parts).strip()

        if not note_text:
            blocked.append({**m, "block_reason": "empty_note_text"})
            continue

        rows.append({
            "source_system": "structured_whisky_source_01",
            "source_path": source_path,
            "source_id": m.get("source_id", ""),
            "whisky_id": m.get("matched_whisky_id", ""),
            "matched_whisky_name": m.get("matched_whisky_name", ""),
            "source_name": m.get("source_name", ""),
            "match_status": status,
            "match_score": m.get("best_score", ""),
            "note_language": "en",
            "note_type": "external_structured_preview",
            "approval_status": "staging_pending_review",
            "source_abv": m.get("source_abv", ""),
            "source_age": m.get("source_age", ""),
            "source_bottler": m.get("source_bottler", ""),
            "source_external_ids": m.get("source_external_ids", ""),
            "note_text": note_text,
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source_system", "source_path", "source_id", "whisky_id",
        "matched_whisky_name", "source_name", "match_status", "match_score",
        "note_language", "note_type", "approval_status",
        "source_abv", "source_age", "source_bottler", "source_external_ids",
        "note_text",
    ]
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    blocked_path = out_path.with_name(out_path.stem + "_blocked.csv")
    block_fields = sorted({k for r in blocked for k in r.keys()}) if blocked else ["block_reason"]
    with blocked_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=block_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(blocked)

    lines = []
    lines.append("# Structured Whisky Source 01 Tasting Note Preview")
    lines.append("")
    lines.append(f"- Matches input: `{matches_path}`")
    lines.append(f"- Preview output: `{out_path}`")
    lines.append(f"- Blocked output: `{blocked_path}`")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    lines.append(f"- candidate preview rows: {len(rows)}")
    lines.append(f"- blocked rows: {len(blocked)}")
    lines.append("")
    lines.append("## Gate")
    lines.append("")
    if rows:
        lines.append("- Gate: **GO_MANUAL_REVIEW**")
    else:
        lines.append("- Gate: **NO-GO**")
    lines.append("- Production DB write: **NO**")
    lines.append("- staging_tasting_notes write: **NO**")
    lines.append("")
    lines.append("## Recommendation")
    lines.append("")
    lines.append("- Review CSV manually before any DB apply.")
    lines.append("- Prefer only `high` matches for first apply.")
    lines.append("- Keep `review` and `manual` rows in review queue.")
    lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"wrote: {out_path}")
    print(f"wrote: {blocked_path}")
    print(f"wrote: {report_path}")


if __name__ == "__main__":
    main()

