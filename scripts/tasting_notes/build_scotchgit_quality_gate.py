import csv
import hashlib
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parents[2]
CANDIDATE_CSV = BASE_DIR / "data" / "output" / "scotchgit_review_candidates.csv"
DB_PATH = BASE_DIR / "output" / "import" / "production.db"
REPORT_189 = BASE_DIR / "output" / "reports" / "189_scotchgit_real_candidate_report.md"
REPORT_190 = BASE_DIR / "output" / "reports" / "190_scotchgit_match_quality_report.md"
REPORT_OUT = BASE_DIR / "output" / "reports" / "191_scotchgit_candidate_quality_gate.md"
RISK_CSV_OUT = BASE_DIR / "output" / "reports" / "192_scotchgit_candidate_risk_samples.csv"

RISK_FIELDS = [
    "risk_type",
    "severity",
    "product_name",
    "source_url",
    "reviewer",
    "review_count",
    "rating",
    "avg_rating",
    "matched_master_whisky_id",
    "match_score",
    "match_status",
    "detail",
]


def clean(value):
    return (value or "").strip()


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_candidates(errors):
    if not CANDIDATE_CSV.exists():
        errors.append(f"Missing candidate CSV: {CANDIDATE_CSV}")
        return []
    try:
        with CANDIDATE_CSV.open("r", encoding="utf-8-sig", newline="") as fh:
            return list(csv.DictReader(fh))
    except UnicodeDecodeError:
        errors.append("Candidate CSV required replacement decoding.")
        with CANDIDATE_CSV.open("r", encoding="utf-8", errors="replace", newline="") as fh:
            return list(csv.DictReader(fh))
    except Exception as exc:
        errors.append(f"Failed to read candidate CSV: {exc}")
        return []


def load_master_ids_read_only(errors):
    if not DB_PATH.exists():
        errors.append(f"Missing production DB: {DB_PATH}")
        return set(), "", ""

    before_hash = sha256_file(DB_PATH)
    ids = set()
    try:
        uri = DB_PATH.resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        with conn:
            rows = conn.execute("SELECT whisky_id FROM whiskies").fetchall()
        ids = {clean(row[0]) for row in rows if clean(row[0])}
    except Exception as exc:
        errors.append(f"Failed to read production DB in read-only mode: {exc}")
    finally:
        try:
            conn.close()
        except Exception:
            pass
    after_hash = sha256_file(DB_PATH)
    return ids, before_hash, after_hash


def is_reddit_url(url):
    parsed = urlparse(clean(url))
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return parsed.scheme in {"http", "https"} and host in {"reddit.com", "old.reddit.com"}


def score_bucket(row):
    try:
        score = int(float(clean(row.get("match_score")) or 0))
    except ValueError:
        score = 0
    if score >= 92:
        return "High"
    if score >= 80:
        return "Medium"
    return "Low"


def add_risk(risks, risk_type, severity, row, detail):
    risks.append(
        {
            "risk_type": risk_type,
            "severity": severity,
            "product_name": clean(row.get("product_name")),
            "source_url": clean(row.get("source_url")),
            "reviewer": clean(row.get("reviewer")),
            "review_count": clean(row.get("review_count")),
            "rating": clean(row.get("rating")),
            "avg_rating": clean(row.get("avg_rating")),
            "matched_master_whisky_id": clean(row.get("matched_master_whisky_id")),
            "match_score": clean(row.get("match_score")),
            "match_status": clean(row.get("match_status")),
            "detail": detail,
        }
    )


def main():
    errors = []
    rows = read_candidates(errors)
    master_ids, db_hash_before, db_hash_after = load_master_ids_read_only(errors)

    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    RISK_CSV_OUT.parent.mkdir(parents=True, exist_ok=True)

    product_names = [clean(row.get("product_name")) for row in rows]
    source_urls = [clean(row.get("source_url")) for row in rows]
    reviewers = [clean(row.get("reviewer")) for row in rows]
    rating_signals = [clean(row.get("rating")) or clean(row.get("avg_rating")) for row in rows]
    raw_ratings = [clean(row.get("rating")) for row in rows]

    product_counter = Counter(product_names)
    url_counter = Counter(source_urls)
    duplicate_source_url_count = sum(count - 1 for url, count in url_counter.items() if url and count > 1)

    products_by_url = defaultdict(set)
    for row in rows:
        products_by_url[clean(row.get("source_url"))].add(clean(row.get("product_name")))
    multi_product_url = {
        url: sorted(products)
        for url, products in products_by_url.items()
        if url and len(products) > 1
    }

    match_status_counts = Counter(clean(row.get("match_status")) or "blank" for row in rows)
    bucket_counts = Counter(score_bucket(row) for row in rows)
    matched_ids = [clean(row.get("matched_master_whisky_id")) for row in rows if clean(row.get("matched_master_whisky_id"))]
    matched_in_db = sum(1 for whisky_id in matched_ids if whisky_id in master_ids)
    matched_missing_from_db = sum(1 for whisky_id in matched_ids if whisky_id not in master_ids)
    unmatched_count = len(rows) - len(matched_ids)

    fail_checks = []
    risks = []

    sample_url_rows = [row for row in rows if "sample-" in clean(row.get("source_url")).lower()]
    blank_product_rows = [row for row in rows if not clean(row.get("product_name"))]
    blank_url_rows = [row for row in rows if not clean(row.get("source_url"))]
    blank_reviewer_rows = [row for row in rows if not clean(row.get("reviewer"))]
    blank_rating_signal_rows = [row for row in rows if not (clean(row.get("rating")) or clean(row.get("avg_rating")))]
    non_reddit_rows = [row for row in rows if clean(row.get("source_url")) and not is_reddit_url(row.get("source_url"))]

    critical_groups = [
        ("sample_url", sample_url_rows, "source_url contains sample-"),
        ("blank_product_name", blank_product_rows, "product_name is blank"),
        ("blank_source_url", blank_url_rows, "source_url is blank"),
        ("blank_reviewer", blank_reviewer_rows, "reviewer is blank"),
        ("blank_rating_signal", blank_rating_signal_rows, "rating and avg_rating are blank"),
        ("non_reddit_url", non_reddit_rows, "source_url is not reddit.com or old.reddit.com"),
    ]
    for risk_type, group, detail in critical_groups:
        if group:
            fail_checks.append(f"{risk_type}: {len(group)}")
            for row in group[:100]:
                add_risk(risks, risk_type, "FAIL", row, detail)

    for row in sorted(rows, key=lambda item: int(float(clean(item.get("match_score")) or 0)))[:100]:
        if score_bucket(row) == "Low":
            add_risk(risks, "low_fuzzy_score", "REVIEW", row, "Low match bucket; review before import.")

    for url, products in sorted(multi_product_url.items(), key=lambda item: len(item[1]), reverse=True)[:100]:
        first_row = next(row for row in rows if clean(row.get("source_url")) == url)
        add_risk(
            risks,
            "source_url_multiple_products",
            "REVIEW",
            first_row,
            f"{len(products)} product_name values share this source_url.",
        )

    review_heavy_rows = sorted(
        rows,
        key=lambda row: int(float(clean(row.get("review_count")) or 0)),
        reverse=True,
    )[:20]

    db_changed = bool(db_hash_before and db_hash_after and db_hash_before != db_hash_after)
    if db_changed:
        fail_checks.append("production_db_hash_changed")

    high_confidence_ratio = (bucket_counts["High"] / len(rows) * 100) if rows else 0
    go_no_go = "GO" if not fail_checks and rows else "NO-GO"

    with RISK_CSV_OUT.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=RISK_FIELDS)
        writer.writeheader()
        writer.writerows(risks)

    with REPORT_OUT.open("w", encoding="utf-8") as fh:
        fh.write("# ScotchGit Candidate Quality Gate\n\n")
        fh.write("## Decision\n\n")
        fh.write(f"- production import decision: **{go_no_go}**\n")
        fh.write(f"- fail checks: {', '.join(fail_checks) if fail_checks else 'None'}\n")
        fh.write(f"- production.db changed: {'YES' if db_changed else 'NO'}\n")
        fh.write(f"- production.db read mode: SQLite URI `mode=ro`\n\n")

        fh.write("## Input Files\n\n")
        for path in (CANDIDATE_CSV, DB_PATH, REPORT_189, REPORT_190):
            fh.write(f"- `{path.as_posix()}` exists: {'YES' if path.exists() else 'NO'}\n")
        fh.write("\n")

        fh.write("## Counts\n\n")
        fh.write(f"- total rows: {len(rows)}\n")
        fh.write(f"- unique product_name: {len(set(name for name in product_names if name))}\n")
        fh.write(f"- unique source_url: {len(set(url for url in source_urls if url))}\n")
        fh.write(f"- duplicate source_url count: {duplicate_source_url_count}\n")
        fh.write(f"- source_url values with multiple product_name values: {len(multi_product_url)}\n")
        fh.write(f"- raw rating column blank rows: {sum(1 for value in raw_ratings if not value)}\n")
        fh.write(f"- usable rating signal blank rows: {len(blank_rating_signal_rows)}\n\n")

        fh.write("## Match Confidence Distribution\n\n")
        for status, count in sorted(match_status_counts.items()):
            fh.write(f"- {status}: {count}\n")
        fh.write("\n")
        fh.write("## Match Buckets\n\n")
        for bucket in ("High", "Medium", "Low"):
            count = bucket_counts[bucket]
            pct = (count / len(rows) * 100) if rows else 0
            fh.write(f"- {bucket}: {count} ({pct:.2f}%)\n")
        fh.write(f"- high confidence ratio: {high_confidence_ratio:.2f}%\n\n")

        fh.write("## Master DB Match Audit\n\n")
        fh.write(f"- matched whisky_id values in CSV: {len(matched_ids)}\n")
        fh.write(f"- matched whisky_id values found in production.db: {matched_in_db}\n")
        fh.write(f"- matched whisky_id values missing from production.db: {matched_missing_from_db}\n")
        fh.write(f"- rows without matched_master_whisky_id: {unmatched_count}\n\n")

        fh.write("## Domain And Required Field Checks\n\n")
        fh.write(f"- sample URL rows: {len(sample_url_rows)}\n")
        fh.write(f"- blank product_name rows: {len(blank_product_rows)}\n")
        fh.write(f"- blank source_url rows: {len(blank_url_rows)}\n")
        fh.write(f"- blank reviewer rows: {len(blank_reviewer_rows)}\n")
        fh.write(f"- blank rating signal rows: {len(blank_rating_signal_rows)}\n")
        fh.write(f"- non-Reddit source_url rows: {len(non_reddit_rows)}\n\n")

        fh.write("## Very Low Fuzzy Score Samples\n\n")
        low_rows = sorted(rows, key=lambda item: int(float(clean(item.get("match_score")) or 0)))[:20]
        for row in low_rows:
            fh.write(
                f"- {clean(row.get('product_name'))} | score={clean(row.get('match_score'))} | "
                f"status={clean(row.get('match_status'))} | url={clean(row.get('source_url'))}\n"
            )
        fh.write("\n")

        fh.write("## Top 20 High Review Count Products\n\n")
        for row in review_heavy_rows:
            fh.write(
                f"- {clean(row.get('product_name'))} | reviews={clean(row.get('review_count'))} | "
                f"reviewer={clean(row.get('reviewer'))} | score={clean(row.get('match_score'))}\n"
            )
        fh.write("\n")

        fh.write("## Shared Source URL Samples\n\n")
        for url, products in sorted(multi_product_url.items(), key=lambda item: len(item[1]), reverse=True)[:20]:
            fh.write(f"- {url} | products={len(products)}\n")
        fh.write("\n")

        fh.write("## Script Warnings\n\n")
        if errors:
            for error in errors:
                fh.write(f"- {error}\n")
        else:
            fh.write("- None\n")

    print(f"Quality gate decision: {go_no_go}")
    print(f"Rows checked: {len(rows)}")
    print(f"High confidence ratio: {high_confidence_ratio:.2f}%")
    print(f"Risk samples written: {len(risks)}")
    print(f"Report written: {REPORT_OUT}")
    print(f"Risk CSV written: {RISK_CSV_OUT}")


if __name__ == "__main__":
    main()
