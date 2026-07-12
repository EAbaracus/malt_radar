from __future__ import annotations

from pathlib import Path

import pandas as pd


INPUT = Path("data/output/whiskyfun_product_candidate_review.csv")
AUDIT_OUT = Path("data/output/whiskyfun_product_candidate_quality_audit.csv")
SUMMARY_OUT = Path("data/output/whiskyfun_product_candidate_quality_summary.csv")
REPORT_OUT = Path("output/reports/323_12u_product_candidate_quality_audit_report.md")
GATE_OUT = Path("output/reports/324_12u_product_candidate_quality_audit_gate.txt")

FORBIDDEN_TEXT_FIELDS = {"review_text", "nose", "mouth", "finish", "comments", "nmf"}
FORBIDDEN_PUBLIC_SOURCE_FIELDS = {"source_url", "source_name", "source_id", "source_system"}

CASK_TERMS = {
    "bourbon",
    "sherry",
    "oloroso",
    "px",
    "port",
    "madeira",
    "rum",
    "wine",
    "sauternes",
    "marsala",
    "mizunara",
}

RELEASE_TERMS = {
    "storm",
    "dark storm",
    "tempest",
    "batch",
    "release",
    "limited",
    "edition",
    "single cask",
    "cask strength",
}


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).lower()


def contained_terms(value: object, terms: set[str]) -> set[str]:
    value_text = text(value)
    return {term for term in terms if term in value_text}


def quality_flags(row: pd.Series) -> list[str]:
    raw_name = text(row.get("whisky_name_raw", ""))
    matched_name = text(row.get("matched_whisky_name", ""))
    flags: list[str] = []

    raw_casks = contained_terms(raw_name, CASK_TERMS)
    matched_casks = contained_terms(matched_name, CASK_TERMS)
    if raw_casks and matched_casks and raw_casks != matched_casks:
        flags.append("cask_term_mismatch")
    elif raw_casks and not matched_casks:
        flags.append("raw_cask_term_missing_in_match")
    elif matched_casks and not raw_casks:
        flags.append("matched_cask_term_not_in_raw")

    raw_releases = contained_terms(raw_name, RELEASE_TERMS)
    matched_releases = contained_terms(matched_name, RELEASE_TERMS)
    if raw_releases and matched_releases and raw_releases != matched_releases:
        flags.append("release_term_mismatch")
    elif raw_releases and not matched_releases:
        flags.append("raw_release_term_missing_in_match")
    elif matched_releases and not raw_releases:
        flags.append("matched_release_term_not_in_raw")

    if "storm" in raw_name and "dark storm" in matched_name:
        flags.append("storm_dark_storm_mismatch")

    if "age of discovery" in raw_name and "madeira" in matched_name and "madeira" not in raw_name:
        flags.append("age_of_discovery_cask_mismatch")

    if "batch" in raw_name and "batch" not in matched_name:
        flags.append("batch_missing_in_match")

    if "single cask" in raw_name and "single cask" not in matched_name:
        flags.append("single_cask_missing_in_match")

    return flags


def main() -> int:
    AUDIT_OUT.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    GATE_OUT.parent.mkdir(parents=True, exist_ok=True)

    if not INPUT.exists():
        write_text(GATE_OUT, "NO_GO_INPUT_MISSING\n")
        write_text(REPORT_OUT, "# 12U Product Candidate Quality Audit\n\nInput CSV missing.\n")
        return 1

    df = pd.read_csv(INPUT)

    text_leaks = sorted(FORBIDDEN_TEXT_FIELDS.intersection(df.columns))
    if text_leaks:
        write_text(GATE_OUT, "NO_GO_FULL_TEXT_LEAK\n")
        write_text(REPORT_OUT, f"# 12U Product Candidate Quality Audit\n\nForbidden text fields found: {text_leaks}\n")
        return 1

    source_leaks = sorted(FORBIDDEN_PUBLIC_SOURCE_FIELDS.intersection(df.columns))
    if source_leaks:
        write_text(GATE_OUT, "NO_GO_SOURCE_FIELD_LEAK\n")
        write_text(REPORT_OUT, f"# 12U Product Candidate Quality Audit\n\nPublic source fields found: {source_leaks}\n")
        return 1

    if df.empty:
        write_text(GATE_OUT, "NO_GO_INPUT_MISSING\nNo candidate rows\n")
        write_text(REPORT_OUT, "# 12U Product Candidate Quality Audit\n\nNo candidate rows found.\n")
        return 1

    df["quality_flags"] = df.apply(lambda row: "|".join(quality_flags(row)), axis=1)
    df["quality_decision"] = df["quality_flags"].apply(
        lambda flags: "MANUAL_REVIEW_REQUIRED" if flags else "QUALITY_KEEP_CANDIDATE"
    )

    df.to_csv(AUDIT_OUT, index=False)

    decision_counts = df["quality_decision"].value_counts()
    manual_review_count = int((df["quality_decision"] == "MANUAL_REVIEW_REQUIRED").sum())
    keep_count = int((df["quality_decision"] == "QUALITY_KEEP_CANDIDATE").sum())

    flag_counts: dict[str, int] = {}
    for flags in df["quality_flags"].fillna(""):
        for flag in [f for f in str(flags).split("|") if f]:
            flag_counts[flag] = flag_counts.get(flag, 0) + 1

    summary_rows = [
        {"metric": "input_rows", "value": len(df)},
        {"metric": "quality_keep_candidate", "value": keep_count},
        {"metric": "manual_review_required", "value": manual_review_count},
        {"metric": "full_text_leak", "value": 0},
        {"metric": "public_source_field_leak", "value": 0},
    ]

    for key, value in decision_counts.items():
        summary_rows.append({"metric": f"quality_decision:{key}", "value": int(value)})

    for key, value in sorted(flag_counts.items(), key=lambda item: item[1], reverse=True):
        summary_rows.append({"metric": f"quality_flag:{key}", "value": int(value)})

    pd.DataFrame(summary_rows).to_csv(SUMMARY_OUT, index=False)

    gate = "GO_MANUAL_REVIEW_REQUIRED" if manual_review_count else "GO_QUALITY_AUDIT_ONLY"

    report = (
        "# 12U Product Candidate Quality Audit\n\n"
        f"Gate: {gate}\n"
        f"Input rows: {len(df)}\n"
        f"QUALITY_KEEP_CANDIDATE: {keep_count}\n"
        f"MANUAL_REVIEW_REQUIRED: {manual_review_count}\n"
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
    print(f"quality_keep_candidate: {keep_count}")
    print(f"manual_review_required: {manual_review_count}")
    print(f"gate: {gate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
