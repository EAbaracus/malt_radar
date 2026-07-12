from __future__ import annotations

from pathlib import Path

import pandas as pd


INPUT = Path("data/output/whiskyfun_derived_feature_product_match_preview.csv")
PREVIEW_OUT = Path("data/output/whiskyfun_tuned_match_preview.csv")
SUMMARY_OUT = Path("data/output/whiskyfun_tuned_match_summary.csv")
REPORT_OUT = Path("output/reports/319_12s_whiskyfun_matcher_tuning_preview_report.md")
GATE_OUT = Path("output/reports/320_12s_whiskyfun_matcher_tuning_preview_gate.txt")

FORBIDDEN_TEXT_FIELDS = {"review_text", "nose", "mouth", "finish", "comments", "nmf"}
FORBIDDEN_PUBLIC_SOURCE_FIELDS = {"source_url", "source_name", "source_id", "source_system"}
STRONG_CONFLICTS = {"age_mismatch", "vintage_mismatch"}
SOFT_CONFLICTS = {"cask_mismatch", "bottler_mismatch", "release_mismatch", "low_name_score"}


def split_flags(value: object) -> set[str]:
    if pd.isna(value):
        return set()
    text = str(value).strip()
    if not text or text.lower() in {"none", "nan", "[]"}:
        return set()
    for sep in ["|", ";", ","]:
        if sep in text:
            return {part.strip() for part in text.split(sep) if part.strip()}
    return {text}


def truthy(value: object) -> bool:
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def score_value(value: object) -> float:
    if pd.isna(value):
        return 0.0
    try:
        return float(value)
    except ValueError:
        return 0.0


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def tune_row(row: pd.Series) -> str:
    decision = str(row.get("decision", "")).strip()
    flags = split_flags(row.get("conflict_flags", ""))
    score = score_value(row.get("name_match_score", 0))
    distillery_match = truthy(row.get("distillery_match", False))

    if decision == "KEEP_PRODUCT_FEATURE":
        return "KEEP_PRODUCT_FEATURE"

    if decision == "REVIEW_PRODUCT_FEATURE":
        if score >= 94 and distillery_match and not flags.intersection(STRONG_CONFLICTS):
            return "KEEP_PRODUCT_FEATURE_CANDIDATE"
        return "REVIEW_PRODUCT_FEATURE_TUNED"

    if decision == "REJECT_CONFLICT":
        if flags.intersection(STRONG_CONFLICTS):
            return "REJECT_CONFLICT_STRONG"
        if not flags or flags.issubset(SOFT_CONFLICTS):
            return "REVIEW_CONFLICT_TUNED"
        return "REJECT_CONFLICT_STRONG"

    if decision == "REJECT_LOW_CONFIDENCE":
        return "REJECT_LOW_CONFIDENCE"

    if decision == "KEEP_DISTILLERY_FEATURE_ONLY":
        return "KEEP_DISTILLERY_FEATURE_ONLY"

    return f"{decision}_UNCHANGED" if decision else "MISSING_DECISION"


def main() -> int:
    PREVIEW_OUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    GATE_OUT.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT.exists():
        write_text(GATE_OUT, "NO_GO_INPUT_MISSING\n")
        write_text(REPORT_OUT, "# 12S Matcher Tuning Preview\n\nInput CSV missing.\n")
        return 1

    df = pd.read_csv(INPUT)

    text_leaks = sorted(FORBIDDEN_TEXT_FIELDS.intersection(df.columns))
    if text_leaks:
        write_text(GATE_OUT, "NO_GO_FULL_TEXT_LEAK\n")
        write_text(REPORT_OUT, f"# 12S Matcher Tuning Preview\n\nForbidden text fields found: {text_leaks}\n")
        return 1

    if "decision" not in df.columns:
        write_text(GATE_OUT, "NO_GO_INPUT_MISSING\nMissing decision column\n")
        write_text(REPORT_OUT, "# 12S Matcher Tuning Preview\n\nMissing required column: decision.\n")
        return 1

    df["tuned_decision"] = df.apply(tune_row, axis=1)

    output_df = df.drop(columns=[c for c in FORBIDDEN_TEXT_FIELDS if c in df.columns], errors="ignore")
    output_df = output_df.drop(columns=[c for c in FORBIDDEN_PUBLIC_SOURCE_FIELDS if c in output_df.columns], errors="ignore")

    source_leaks = sorted(FORBIDDEN_PUBLIC_SOURCE_FIELDS.intersection(output_df.columns))
    if source_leaks:
        write_text(GATE_OUT, "NO_GO_SOURCE_FIELD_LEAK\n")
        write_text(REPORT_OUT, f"# 12S Matcher Tuning Preview\n\nPublic source fields leaked: {source_leaks}\n")
        return 1

    output_df.to_csv(PREVIEW_OUT, index=False)

    original_counts = df["decision"].fillna("MISSING").value_counts()
    tuned_counts = df["tuned_decision"].fillna("MISSING").value_counts()

    keep_candidates = int((df["tuned_decision"] == "KEEP_PRODUCT_FEATURE_CANDIDATE").sum())
    review_conflict_tuned = int((df["tuned_decision"] == "REVIEW_CONFLICT_TUNED").sum())
    strong_conflicts = int((df["tuned_decision"] == "REJECT_CONFLICT_STRONG").sum())

    summary_rows = [
        {"metric": "total_rows", "value": len(df)},
        {"metric": "keep_product_feature_candidate", "value": keep_candidates},
        {"metric": "review_conflict_tuned", "value": review_conflict_tuned},
        {"metric": "reject_conflict_strong", "value": strong_conflicts},
        {"metric": "full_text_leak", "value": 0},
        {"metric": "public_source_field_leak", "value": 0},
    ]

    for key, value in original_counts.items():
        summary_rows.append({"metric": f"original_decision:{key}", "value": int(value)})

    for key, value in tuned_counts.items():
        summary_rows.append({"metric": f"tuned_decision:{key}", "value": int(value)})

    pd.DataFrame(summary_rows).to_csv(SUMMARY_OUT, index=False)

    gate = "GO_PRODUCT_CANDIDATES_FOUND" if keep_candidates > 0 else "GO_TUNING_PREVIEW_ONLY"

    report = (
        "# 12S Matcher Tuning Preview\n\n"
        f"Gate: {gate}\n"
        f"Total rows: {len(df)}\n"
        f"KEEP_PRODUCT_FEATURE_CANDIDATE: {keep_candidates}\n"
        f"REVIEW_CONFLICT_TUNED: {review_conflict_tuned}\n"
        f"REJECT_CONFLICT_STRONG: {strong_conflicts}\n"
        "Full text leak: 0\n"
        "Public source field leak: 0\n"
        "production.db used: No\n\n"
        "Original decisions:\n"
        f"{original_counts.to_string()}\n\n"
        "Tuned decisions:\n"
        f"{tuned_counts.to_string()}\n\n"
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


    print(f"rows: {len(df)}")
    print(f"gate: {gate}")
    print(f"keep_product_feature_candidate: {keep_candidates}")
    print(f"review_conflict_tuned: {review_conflict_tuned}")
    print(f"reject_conflict_strong: {strong_conflicts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())