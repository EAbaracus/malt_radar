import csv
import os
from collections import Counter, defaultdict


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "output")
REPORTS_DIR = os.path.join(BASE_DIR, "output", "reports")

CSV_FILES = [
    "real_masterofmalt_tasting_note_candidates.csv",
    "real_whiskynotes_tasting_note_candidates.csv",
    "real_whiskyedition_tasting_note_candidates.csv",
    "real_twe_flavour_category_candidates.csv",
    "real_whiskybase_tasting_note_candidates.csv",
]

FIELDS = [
    "source_system",
    "source_type",
    "product_name",
    "normalized_product_name",
    "source_url",
    "nose",
    "palate",
    "finish",
    "conclusion",
    "score",
    "rating",
    "price",
    "top_flavors",
    "source_profile",
    "converted_flavor_profile",
    "flavour_camp",
    "similar_whiskies",
    "source_verified",
    "matched_master_whisky_id",
    "match_score",
    "match_method",
    "match_status",
    "approval_status",
    "import_recommendation",
    "notes_for_review",
]


def read_rows(filename):
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def is_tasting_row(row):
    return "tasting_note" in (row.get("source_type") or "")


def has_note(row):
    return any((row.get(field) or "").strip() for field in ("nose", "palate", "finish", "conclusion"))


def main():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    rows_by_file = {filename: read_rows(filename) for filename in CSV_FILES}
    all_rows = [(filename, row) for filename, rows in rows_by_file.items() for row in rows]

    errors = []
    warnings = []
    source_counts = Counter()
    match_counts = Counter()
    match_by_source = defaultdict(Counter)
    urls = []

    for filename, row in all_rows:
        source = row.get("source_system", "").strip() or filename
        source_counts[source] += 1
        url = (row.get("source_url") or "").strip()
        urls.append(url)

        missing = [field for field in FIELDS if field not in row]
        if missing:
            errors.append(f"{filename}: missing columns {', '.join(missing)}")
        if not url:
            errors.append(f"{filename}: source_url is empty")
        if any(token in url.lower() for token in ("sample", "placeholder", "test", "fake")):
            errors.append(f"{filename}: forbidden sample/mock URL token in {url}")
        if not (row.get("product_name") or "").strip():
            errors.append(f"{filename}: product_name is empty at {url}")
        if is_tasting_row(row) and not has_note(row):
            errors.append(f"{filename}: tasting-note row has no nose/palate/finish/conclusion at {url}")
        if filename == "real_twe_flavour_category_candidates.csv":
            if any((row.get(field) or "").strip() for field in ("nose", "palate", "finish", "conclusion")):
                errors.append(f"{filename}: TWE row contains tasting-note fields at {url}")
            if not (row.get("flavour_camp") or row.get("source_profile") or "").strip():
                errors.append(f"{filename}: TWE row has no flavour category at {url}")
        if filename == "real_whiskybase_tasting_note_candidates.csv" and (row.get("source_verified") or "").strip() != "0":
            errors.append(f"{filename}: Whiskybase source_verified must be 0 at {url}")

        if not (row.get("match_method") or "").strip():
            errors.append(f"{filename}: match_method is empty at {url}")
        if not (row.get("match_status") or "").strip():
            errors.append(f"{filename}: match_status is empty at {url}")
        else:
            status = row.get("match_status", "").strip()
            match_counts[status] += 1
            match_by_source[source][status] += 1
        try:
            int(float(row.get("match_score") or 0))
        except ValueError:
            errors.append(f"{filename}: match_score is not numeric at {url}")

    duplicate_urls = sorted(url for url, count in Counter(urls).items() if url and count > 1)
    for url in duplicate_urls:
        errors.append(f"duplicate source_url: {url}")

    usable_sources = sum(1 for rows in rows_by_file.values() if rows)
    sample_mock_rows = [err for err in errors if "forbidden sample/mock" in err]
    duplicate_count = len(duplicate_urls)
    empty_product_count = sum(1 for err in errors if "product_name is empty" in err)
    empty_note_count = sum(1 for err in errors if "tasting-note row has no" in err)

    if sample_mock_rows or duplicate_count or empty_product_count or empty_note_count:
        decision = "FIX_REQUIRED"
    elif usable_sources >= 3:
        decision = "GO"
    elif usable_sources >= 1:
        decision = "PARTIAL"
    else:
        decision = "BLOCKED"

    validation_lines = [
        "# Real External Candidate Validation Report",
        "",
        f"Decision: {decision}",
        f"Usable candidate sources: {usable_sources}",
        f"Total candidate rows: {len(all_rows)}",
        f"Sample/mock URL rows: {len(sample_mock_rows)}",
        f"Duplicate source_url count: {duplicate_count}",
        f"Empty product_name count: {empty_product_count}",
        f"Empty tasting-note row count: {empty_note_count}",
        "",
        "## File Counts",
    ]
    for filename, rows in rows_by_file.items():
        validation_lines.append(f"- {filename}: {len(rows)} rows")
    validation_lines.append("")
    validation_lines.append("## Errors")
    validation_lines.extend([f"- {err}" for err in errors] if errors else ["None"])
    if warnings:
        validation_lines.append("")
        validation_lines.append("## Warnings")
        validation_lines.extend(f"- {warning}" for warning in warnings)

    with open(os.path.join(REPORTS_DIR, "195_real_external_candidate_validation_report.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(validation_lines) + "\n")

    match_lines = [
        "# Real External Match Quality Report",
        "",
        "## Overall",
    ]
    for status in ("high_confidence_match", "needs_review", "unmatched"):
        match_lines.append(f"- {status}: {match_counts[status]}")
    match_lines.append("")
    match_lines.append("## By Source")
    for source, counts in sorted(match_by_source.items()):
        match_lines.append(f"### {source}")
        for status in ("high_confidence_match", "needs_review", "unmatched"):
            match_lines.append(f"- {status}: {counts[status]}")
    with open(os.path.join(REPORTS_DIR, "196_real_external_match_quality_report.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(match_lines) + "\n")

    gate_lines = [
        "11C-REAL-SOURCES Real External Source Go/No-Go Gate",
        "===================================================",
        f"Decision: {decision}",
        f"Usable candidate sources: {usable_sources}",
        f"Total candidate rows: {len(all_rows)}",
        f"Sample/mock URL rows: {len(sample_mock_rows)}",
        f"Duplicate source_url count: {duplicate_count}",
        f"Empty product_name count: {empty_product_count}",
        f"Empty tasting-note row count: {empty_note_count}",
    ]
    if errors:
        gate_lines.extend(["", "Issues:"])
        gate_lines.extend(f"- {err}" for err in errors)
    with open(os.path.join(REPORTS_DIR, "197_real_external_source_go_no_go_gate.txt"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(gate_lines) + "\n")

    print(f"Validation finished. Decision: {decision}")
    print(f"Usable candidate sources: {usable_sources}")
    print(f"Total candidate rows: {len(all_rows)}")


if __name__ == "__main__":
    main()
