from __future__ import annotations

from pathlib import Path

import pandas as pd


INPUT = Path("data/output/whiskyfun_tuned_match_preview.csv")
REVIEW_OUT = Path("data/output/whiskyfun_product_candidate_review.csv")
SUMMARY_OUT = Path("data/output/whiskyfun_product_candidate_review_summary.csv")
REPORT_OUT = Path("output/reports/321_12t_product_candidate_review_preview_report.md")
GATE_OUT = Path("output/reports/322_12t_product_candidate_review_preview_gate.txt")

FORBIDDEN_TEXT_FIELDS = {"review_text", "nose", "mouth", "finish", "comments", "nmf"}
FORBIDDEN_PUBLIC_SOURCE_FIELDS = {"source_url", "source_name", "source_id", "source_system"}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    REVIEW_OUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    GATE_OUT.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT.exists():
        write_text(GATE_OUT, "NO_GO_INPUT_MISSING\n")
        write_text(REPORT_OUT, "# 12T Product Candidate Review Preview\n\nInput CSV missing.\n")
        return 1

    df = pd.read_csv(INPUT)

    text_leaks = sorted(FORBIDDEN_TEXT_FIELDS.intersection(df.columns))
    if text_leaks:
        write_text(GATE_OUT, "NO_GO_FULL_TEXT_LEAK\n")
        write_text(REPORT_OUT, f"# 12T Product Candidate Review Preview\n\nForbidden text fields found: {text_leaks}\n")
        return 1

    source_leaks = sorted(FORBIDDEN_PUBLIC_SOURCE_FIELDS.intersection(df.columns))
    if source_leaks:
        write_text(GATE_OUT, "NO_GO_SOURCE_FIELD_LEAK\n")
        write_text(REPORT_OUT, f"# 12T Product Candidate Review Preview\n\nPublic source fields found: {source_leaks}\n")
        return 1

    if "tuned_decision" not in df.columns:
        write_text(GATE_OUT, "NO_GO_INPUT_MISSING\nMissing tuned_decision column\n")
        write_text(REPORT_OUT, "# 12T Product Candidate Review Preview\n\nMissing required column: tuned_decision.\n")
        return 1

    candidates = df[df["tuned_decision"] == "KEEP_PRODUCT_FEATURE_CANDIDATE"].copy()

    preferred_cols = [
        "dedupe_hash",
        "whisky_name_raw",
        "distillery",
        "source_score",
        "review_year",
        "review_date",
        "matched_whisky_id",
        "matched_whisky_name",
        "matched_distillery",
        "name_match_score",
        "distillery_match",
        "conflict_flags",
        "decision",
        "decision_reason",
        "tuned_decision",
        "internal_audit_only",
        "internal_source_url",
    ]

    safe_cols = [c for c in preferred_cols if c in candidates.columns]
    candidates = candidates[safe_cols]
    candidates.to_csv(REVIEW_OUT, index=False)

    summary_rows = [
        {"metric": "input_rows", "value": len(df)},
        {"metric": "candidate_rows", "value": len(candidates)},
        {"metric": "full_text_leak", "value": 0},
        {"metric": "public_source_field_leak", "value": 0},
    ]

    if "name_match_score" in candidates.columns and not candidates.empty:
        scores = pd.to_numeric(candidates["name_match_score"], errors="coerce")
        summary_rows.extend([
            {"metric": "min_name_match_score", "value": float(scores.min())},
            {"metric": "avg_name_match_score", "value": float(scores.mean())},
            {"metric": "max_name_match_score", "value": float(scores.max())},
        ])

    pd.DataFrame(summary_rows).to_csv(SUMMARY_OUT, index=False)

    gate = "GO_PRODUCT_REVIEW_PREVIEW_ONLY" if len(candidates) > 0 else "NO_GO_NO_CANDIDATES"

    report = (
        "# 12T Product Candidate Review Preview\n\n"
        f"Gate: {gate}\n"
        f"Input rows: {len(df)}\n"
        f"Candidate rows: {len(candidates)}\n"
        "Full text leak: 0\n"
        "Public source field leak: 0\n"
        "production.db used: No\n"
        "Preview only. No DB writes. No input mutation.\n"
    )

    write_text(REPORT_OUT, report)
    write_text(GATE_OUT, gate + "\n")
    write_text(GATE_OUT, "
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
", encoding="utf-8")


    print(f"input_rows: {len(df)}")
    print(f"candidate_rows: {len(candidates)}")
    print(f"gate: {gate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
