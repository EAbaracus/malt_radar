from __future__ import annotations

from pathlib import Path

import pandas as pd


INPUT = Path("data/output/whiskyfun_product_candidate_quality_audit.csv")
PREVIEW_OUT = Path("data/output/whiskyfun_quality_keep_staging_preview.csv")
SUMMARY_OUT = Path("data/output/whiskyfun_quality_keep_staging_summary.csv")
REPORT_OUT = Path("output/reports/325_12v_quality_keep_staging_preview_report.md")
GATE_OUT = Path("output/reports/326_12v_quality_keep_staging_preview_gate.txt")

FORBIDDEN_TEXT_FIELDS = {"review_text", "nose", "mouth", "finish", "comments", "nmf"}
FORBIDDEN_PUBLIC_SOURCE_FIELDS = {"source_url", "source_name", "source_id", "source_system"}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    PREVIEW_OUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    GATE_OUT.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT.exists():
        write_text(GATE_OUT, "NO_GO_INPUT_MISSING\n")
        write_text(REPORT_OUT, "# 12V Quality Keep Staging Preview\n\nInput CSV missing.\n")
        return 1

    df = pd.read_csv(INPUT)

    text_leaks = sorted(FORBIDDEN_TEXT_FIELDS.intersection(df.columns))
    if text_leaks:
        write_text(GATE_OUT, "NO_GO_FULL_TEXT_LEAK\n")
        write_text(REPORT_OUT, f"# 12V Quality Keep Staging Preview\n\nForbidden text fields found: {text_leaks}\n")
        return 1

    source_leaks = sorted(FORBIDDEN_PUBLIC_SOURCE_FIELDS.intersection(df.columns))
    if source_leaks:
        write_text(GATE_OUT, "NO_GO_SOURCE_FIELD_LEAK\n")
        write_text(REPORT_OUT, f"# 12V Quality Keep Staging Preview\n\nPublic source fields found: {source_leaks}\n")
        return 1

    required = {"quality_decision", "matched_whisky_id", "dedupe_hash"}
    missing = sorted(required - set(df.columns))
    if missing:
        write_text(GATE_OUT, "NO_GO_INPUT_MISSING\nMissing columns: " + ",".join(missing) + "\n")
        write_text(REPORT_OUT, f"# 12V Quality Keep Staging Preview\n\nMissing columns: {missing}\n")
        return 1

    keep = df[df["quality_decision"] == "QUALITY_KEEP_CANDIDATE"].copy()

    staging = pd.DataFrame({
        "whisky_id": keep["matched_whisky_id"],
        "internal_source_system": "whiskyfun_derived",
        "source_record_id": keep["dedupe_hash"],
        "source_score": keep.get("source_score"),
        "review_date": keep.get("review_date"),
        "review_year": keep.get("review_year"),
        "approval_status": "staging_pending_review",
        "internal_audit_only": True,
        "internal_source_url": keep.get("internal_source_url"),
        "matched_whisky_name": keep.get("matched_whisky_name"),
        "whisky_name_raw": keep.get("whisky_name_raw"),
        "name_match_score": keep.get("name_match_score"),
        "quality_decision": keep.get("quality_decision"),
    })

    staging.to_csv(PREVIEW_OUT, index=False)

    summary_rows = [
        {"metric": "input_rows", "value": len(df)},
        {"metric": "quality_keep_rows", "value": len(keep)},
        {"metric": "staging_preview_rows", "value": len(staging)},
        {"metric": "full_text_leak", "value": 0},
        {"metric": "public_source_field_leak", "value": 0},
        {"metric": "db_write", "value": 0},
    ]

    if not staging.empty:
        summary_rows.append({"metric": "unique_whisky_ids", "value": int(staging["whisky_id"].nunique())})
        summary_rows.append({"metric": "duplicate_source_record_id", "value": int(staging["source_record_id"].duplicated().sum())})

    pd.DataFrame(summary_rows).to_csv(SUMMARY_OUT, index=False)

    gate = "GO_STAGING_PREVIEW_ONLY" if len(staging) == 94 else "GO_STAGING_PREVIEW_REVIEW_COUNTS"

    report = (
        "# 12V Quality Keep Staging Preview\n\n"
        f"Gate: {gate}\n"
        f"Input rows: {len(df)}\n"
        f"Quality keep rows: {len(keep)}\n"
        f"Staging preview rows: {len(staging)}\n"
        "Full text leak: 0\n"
        "Public source field leak: 0\n"
        "production.db used: No\n"
        "Preview only. No DB writes. No input mutation.\n"
    )

    write_text(REPORT_OUT, report)
    write_text(GATE_OUT, gate + "\n")
    write_text(
        GATE_OUT,
        "\n"
        "Estimated API Cost: $0.00\n"
        "Actual API Cost: $0.00\n"
        "Local Compute Used: Yes\n"
        "Fully Local Execution: Yes\n",
        encoding="utf-8",
    )


    print(f"input_rows: {len(df)}")
    print(f"quality_keep_rows: {len(keep)}")
    print(f"staging_preview_rows: {len(staging)}")
    print(f"gate: {gate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
