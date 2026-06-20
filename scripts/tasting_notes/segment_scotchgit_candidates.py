import csv
import hashlib
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_CSV = BASE_DIR / "data" / "output" / "scotchgit_review_candidates_normalized.csv"
FALLBACK_INPUT_CSV = BASE_DIR / "data" / "output" / "scotchgit_review_candidates.csv"
DB_PATH = BASE_DIR / "output" / "import" / "production.db"
HIGH_CSV = BASE_DIR / "data" / "output" / "scotchgit_candidates_high_confidence.csv"
MEDIUM_CSV = BASE_DIR / "data" / "output" / "scotchgit_candidates_medium_confidence.csv"
QUARANTINE_CSV = BASE_DIR / "data" / "output" / "scotchgit_candidates_quarantine.csv"
REPORT_PATH = BASE_DIR / "output" / "reports" / "195_scotchgit_candidate_segmentation_v2_report.md"

DESCRIPTOR_PREFIXES = ("smoky", "sweet", "peated", "unpeated", "mystery", "blind", "sample")
SAFE_IMPORT_RECOMMENDATIONS = {"import_ready", "ready_for_import", "safe_import", "safe_for_import"}


def clean(value):
    return (value or "").strip()


def normalized(value):
    return " ".join(clean(value).lower().strip('"').split())


def score(row):
    try:
        return int(float(clean(row.get("match_score")) or 0))
    except ValueError:
        return 0


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_source_verified(row):
    if "source_url_verified" in row:
        return clean(row.get("source_url_verified")) == "1"
    return clean(row.get("source_verified")) == "1"


def is_master_match_verified(row):
    return clean(row.get("master_match_verified")) == "1"


def row_match_status(row):
    return normalized(row.get("normalized_match_status") or row.get("match_status"))


def row_import_recommendation(row):
    return normalized(row.get("normalized_import_recommendation") or row.get("import_recommendation"))


def is_reddit_url(url):
    parsed = urlparse(clean(url))
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return parsed.scheme in {"http", "https"} and host in {"reddit.com", "old.reddit.com"}


def starts_with_descriptor(row):
    name = normalized(row.get("product_name"))
    first_word_match = re.match(r'^[\'"]?([a-z]+)', name)
    first_word = first_word_match.group(1) if first_word_match else ""
    return first_word in DESCRIPTOR_PREFIXES


def read_rows():
    input_path = INPUT_CSV if INPUT_CSV.exists() else FALLBACK_INPUT_CSV
    with input_path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_rows(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    out_fields = fieldnames + ["segment", "quarantine_reasons"]
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=out_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def get_duplicate_url_conflicts(rows):
    names_by_url = defaultdict(set)
    for row in rows:
        url = clean(row.get("source_url"))
        name = normalized(row.get("normalized_product_name") or row.get("product_name"))
        if url and name:
            names_by_url[url].add(name)
    return {url: names for url, names in names_by_url.items() if len(names) > 1}


def quarantine_reasons(row, duplicate_conflict_urls):
    reasons = []
    url = clean(row.get("source_url"))
    match_status = row_match_status(row)
    import_recommendation = row_import_recommendation(row)
    notes = clean(row.get("notes_for_review")).lower()

    if not clean(row.get("matched_master_whisky_id")):
        reasons.append("missing_matched_master_whisky_id")
    if not is_master_match_verified(row):
        reasons.append("master_match_verified_not_1")
    if match_status == "unmatched":
        reasons.append("match_status_unmatched")
    if score(row) < 75:
        reasons.append("match_score_below_75")
    if not is_source_verified(row):
        reasons.append("source_verified_not_1")
    if not is_reddit_url(url):
        reasons.append("non_reddit_domain")
    if url in duplicate_conflict_urls:
        reasons.append("duplicate_source_url_conflict")
    if starts_with_descriptor(row):
        reasons.append("descriptor_product_name_prefix")
    if import_recommendation in {"review_before_import", "quarantine"}:
        reasons.append(import_recommendation)
    if "no whiskyslist.ts metadata match found" in notes:
        reasons.append("missing_whiskyslist_metadata")
    if not clean(row.get("product_name")):
        reasons.append("blank_product_name")
    if not url:
        reasons.append("blank_source_url")
    if not clean(row.get("reviewer")):
        reasons.append("blank_reviewer")
    return reasons


def is_high(row, duplicate_conflict_urls):
    url = clean(row.get("source_url"))
    return (
        is_reddit_url(url)
        and clean(row.get("product_name"))
        and url
        and clean(row.get("reviewer"))
        and is_source_verified(row)
        and is_master_match_verified(row)
        and clean(row.get("matched_master_whisky_id"))
        and row_match_status(row) == "matched"
        and score(row) >= 90
        and url not in duplicate_conflict_urls
        and row_import_recommendation(row) in SAFE_IMPORT_RECOMMENDATIONS | {"candidate_only_high_confidence"}
    )


def is_medium(row, duplicate_conflict_urls):
    url = clean(row.get("source_url"))
    return (
        is_reddit_url(url)
        and clean(row.get("product_name"))
        and url
        and clean(row.get("reviewer"))
        and clean(row.get("matched_master_whisky_id"))
        and row_match_status(row) in {"matched", "review"}
        and 75 <= score(row) < 90
        and url not in duplicate_conflict_urls
        and is_source_verified(row)
        and row_import_recommendation(row) == "manual_review"
    )


def main():
    if not INPUT_CSV.exists() and not FALLBACK_INPUT_CSV.exists():
        raise FileNotFoundError(f"Missing input CSV: {INPUT_CSV}")

    rows = read_rows()
    db_hash_before = sha256_file(DB_PATH) if DB_PATH.exists() else ""
    fieldnames = list(rows[0].keys()) if rows else []
    duplicate_conflict_urls = get_duplicate_url_conflicts(rows)

    high_rows = []
    medium_rows = []
    quarantine_rows = []
    reason_counts = Counter()

    for row in rows:
        row = dict(row)
        reasons = quarantine_reasons(row, duplicate_conflict_urls)
        if is_high(row, duplicate_conflict_urls):
            row["segment"] = "high"
            row["quarantine_reasons"] = ""
            high_rows.append(row)
        elif is_medium(row, duplicate_conflict_urls):
            row["segment"] = "medium"
            row["quarantine_reasons"] = ""
            medium_rows.append(row)
        else:
            row["segment"] = "quarantine"
            row["quarantine_reasons"] = "|".join(reasons or ["does_not_meet_high_or_medium_rules"])
            reason_counts.update(reasons or ["does_not_meet_high_or_medium_rules"])
            quarantine_rows.append(row)

    write_rows(HIGH_CSV, high_rows, fieldnames)
    write_rows(MEDIUM_CSV, medium_rows, fieldnames)
    write_rows(QUARANTINE_CSV, quarantine_rows, fieldnames)

    non_reddit_count = sum(1 for row in rows if clean(row.get("source_url")) and not is_reddit_url(row.get("source_url")))
    unmatched_count = sum(1 for row in rows if row_match_status(row) == "unmatched")
    source_verified_zero_count = sum(1 for row in rows if not is_source_verified(row))
    master_match_verified_count = sum(1 for row in rows if is_master_match_verified(row))
    db_hash_after = sha256_file(DB_PATH) if DB_PATH.exists() else ""
    db_changed = bool(db_hash_before and db_hash_after and db_hash_before != db_hash_after)
    decision = "GO" if high_rows and not medium_rows and not quarantine_rows else "NO-GO"

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as fh:
        fh.write("# ScotchGit Candidate Segmentation V2 Report\n\n")
        fh.write("## Decision\n\n")
        fh.write(f"- production import GO/NO-GO: **{decision}**\n")
        fh.write(f"- production.db changed: {'YES' if db_changed else 'NO'}\n")
        fh.write("- low/unmatched rows are not production candidates.\n")
        fh.write("- normalized source CSV was read only during segmentation.\n")
        fh.write("- production import remains controlled by report/gate output only.\n\n")

        fh.write("## Input\n\n")
        fh.write(f"- input CSV: `{(INPUT_CSV if INPUT_CSV.exists() else FALLBACK_INPUT_CSV).as_posix()}`\n\n")

        fh.write("## Segment Counts\n\n")
        fh.write(f"- total rows: {len(rows)}\n")
        fh.write(f"- high rows: {len(high_rows)}\n")
        fh.write(f"- medium rows: {len(medium_rows)}\n")
        fh.write(f"- quarantine rows: {len(quarantine_rows)}\n")
        fh.write(f"- high unique product_name: {len({clean(row.get('product_name')) for row in high_rows if clean(row.get('product_name'))})}\n")
        fh.write(f"- medium unique product_name: {len({clean(row.get('product_name')) for row in medium_rows if clean(row.get('product_name'))})}\n\n")

        fh.write("## Risk Counts\n\n")
        fh.write(f"- duplicate source_url conflict count: {len(duplicate_conflict_urls)}\n")
        fh.write(f"- reddit dışı domain count: {non_reddit_count}\n")
        fh.write(f"- unmatched count: {unmatched_count}\n")
        fh.write(f"- source_url_verified=0 count: {source_verified_zero_count}\n")
        fh.write(f"- master_match_verified=1 count: {master_match_verified_count}\n\n")

        fh.write("## Quarantine Reason Distribution\n\n")
        if reason_counts:
            for reason, count in reason_counts.most_common():
                fh.write(f"- {reason}: {count}\n")
        else:
            fh.write("- None\n")
        fh.write("\n")

        fh.write("## Top 50 Quarantine Sample\n\n")
        for row in quarantine_rows[:50]:
            fh.write(
                f"- {clean(row.get('product_name'))} | score={clean(row.get('match_score'))} | "
                f"status={row_match_status(row)} | reasons={row['quarantine_reasons']} | "
                f"url={clean(row.get('source_url'))}\n"
            )
        fh.write("\n")

        fh.write("## Output Files\n\n")
        fh.write(f"- `{HIGH_CSV.as_posix()}`\n")
        fh.write(f"- `{MEDIUM_CSV.as_posix()}`\n")
        fh.write(f"- `{QUARANTINE_CSV.as_posix()}`\n")

    print(f"Segmentation complete. total={len(rows)} high={len(high_rows)} medium={len(medium_rows)} quarantine={len(quarantine_rows)}")
    print(f"Decision: {decision}")
    print(f"Report written: {REPORT_PATH}")


if __name__ == "__main__":
    main()
