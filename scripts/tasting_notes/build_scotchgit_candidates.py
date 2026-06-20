import csv
import difflib
import hashlib
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "output" / "import" / "production.db"
SCOTCHFILE_PATH = BASE_DIR / "data" / "external" / "scotchgit" / "scotchfile.csv"
WHISKYS_LIST_PATH = BASE_DIR / "data" / "external" / "scotchgit" / "whiskysList.ts"
OUTPUT_DIR = BASE_DIR / "data" / "output"
REPORTS_DIR = BASE_DIR / "output" / "reports"
CSV_OUT_PATH = OUTPUT_DIR / "scotchgit_review_candidates.csv"
NORMALIZED_CSV_OUT_PATH = OUTPUT_DIR / "scotchgit_review_candidates_normalized.csv"
REAL_REPORT_PATH = REPORTS_DIR / "189_scotchgit_real_candidate_report.md"
MATCH_REPORT_PATH = REPORTS_DIR / "190_scotchgit_match_quality_report.md"
NORMALIZATION_REPORT_PATH = REPORTS_DIR / "194_scotchgit_match_normalization_report.md"

FIELDS = [
    "source_system",
    "source_type",
    "product_name",
    "normalized_product_name",
    "source_url",
    "reviewer",
    "rating",
    "price",
    "region",
    "review_date",
    "review_count",
    "avg_rating",
    "min_rating",
    "max_rating",
    "word_cloud_url",
    "map_x",
    "map_y",
    "source_verified",
    "matched_master_whisky_id",
    "match_score",
    "match_method",
    "match_status",
    "approval_status",
    "import_recommendation",
    "notes_for_review",
]

NORMALIZED_FIELDS = FIELDS + [
    "source_url_verified",
    "master_match_verified",
    "normalized_match_status",
    "normalized_import_recommendation",
    "quarantine_reason",
]


def normalize_text(value):
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def token_set(value):
    return set(re.findall(r"[a-z0-9]+", normalize_text(value)))


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "").strip())


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_reddit_url(url):
    parsed = urlparse(clean_text(url))
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return parsed.scheme in {"http", "https"} and host in {"reddit.com", "old.reddit.com"}


def clean_rating(value):
    text = clean_text(value)
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def first_non_empty(rows, field):
    for row in rows:
        value = clean_text(row.get(field, ""))
        if value:
            return value
    return ""


def first_real_url(rows):
    for row in rows:
        url = clean_text(row.get("Link To Reddit Review", ""))
        if url.lower().startswith(("http://", "https://")) and "sample-" not in url.lower():
            return url
    return ""


def most_common_non_empty(rows, field):
    values = [clean_text(row.get(field, "")) for row in rows]
    values = [value for value in values if value]
    if not values:
        return ""
    counts = Counter(values)
    return counts.most_common(1)[0][0]


def parse_whiskys_list(errors):
    metadata = {}
    if not WHISKYS_LIST_PATH.exists():
        errors.append(f"Missing source file: {WHISKYS_LIST_PATH}")
        return metadata

    try:
        content = WHISKYS_LIST_PATH.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        content = WHISKYS_LIST_PATH.read_text(encoding="utf-8", errors="replace")
        errors.append("whiskysList.ts contained undecodable characters; replacement decoding was used.")
    except Exception as exc:
        errors.append(f"Failed to read whiskysList.ts: {exc}")
        return metadata

    pattern = re.compile(
        r'\[\s*"(?P<name>(?:[^"\\]|\\.)*)"\s*,\s*'
        r'"(?P<code>(?:[^"\\]|\\.)*)"\s*,\s*'
        r'"(?P<word_cloud>(?:[^"\\]|\\.)*)"\s*,\s*'
        r'"(?P<region>(?:[^"\\]|\\.)*)"\s*,\s*'
        r"(?P<x>-?\d+(?:\.\d+)?)\s*,\s*(?P<y>-?\d+(?:\.\d+)?)\s*\]"
    )

    for match in pattern.finditer(content):
        name = clean_text(match.group("name"))
        metadata[normalize_text(name)] = {
            "product_name": name,
            "word_cloud_url": clean_text(match.group("word_cloud")),
            "region": clean_text(match.group("region")),
            "map_x": clean_text(match.group("x")),
            "map_y": clean_text(match.group("y")),
        }

    if not metadata:
        errors.append("No entries parsed from whiskysList.ts.")
    return metadata


def parse_scotchfile(errors):
    groups = defaultdict(list)
    row_count = 0
    skipped_blank_name = 0

    if not SCOTCHFILE_PATH.exists():
        errors.append(f"Missing source file: {SCOTCHFILE_PATH}")
        return groups, row_count, skipped_blank_name

    try:
        fh = SCOTCHFILE_PATH.open("r", encoding="utf-8-sig", newline="")
    except UnicodeDecodeError:
        fh = SCOTCHFILE_PATH.open("r", encoding="utf-8", errors="replace", newline="")
        errors.append("scotchfile.csv contained undecodable characters; replacement decoding was used.")
    except Exception as exc:
        errors.append(f"Failed to open scotchfile.csv: {exc}")
        return groups, row_count, skipped_blank_name

    with fh:
        try:
            reader = csv.DictReader(fh)
            required = {
                "Timestamp",
                "Whisky Name",
                "Reviewer Username",
                "Link To Reddit Review",
                "Rating",
                "Region",
                "Price",
                "Date",
            }
            missing = sorted(required - set(reader.fieldnames or []))
            if missing:
                errors.append(f"scotchfile.csv missing columns: {', '.join(missing)}")
                return groups, row_count, skipped_blank_name

            for row in reader:
                row_count += 1
                product_name = clean_text(row.get("Whisky Name", ""))
                if not product_name:
                    skipped_blank_name += 1
                    continue
                groups[product_name].append(row)
        except Exception as exc:
            errors.append(f"Failed while parsing scotchfile.csv near row {row_count + 1}: {exc}")

    return groups, row_count, skipped_blank_name


class MasterWhiskyMatcher:
    def __init__(self, errors):
        self.whiskies = []
        self.match_targets = []
        self.db_hash_before = ""
        self.db_hash_after = ""
        if not DB_PATH.exists():
            errors.append(f"Missing master DB: {DB_PATH}")
            return
        conn = None
        try:
            self.db_hash_before = sha256_file(DB_PATH)
            conn = sqlite3.connect(DB_PATH.resolve().as_uri() + "?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            with conn:
                rows = conn.execute(
                    """
                    SELECT whisky_id, name, brand, region, country, type, age
                    FROM whiskies
                    """
                ).fetchall()
            self.whiskies = [dict(row) for row in rows]
            self.match_targets = self._build_match_targets()
        except Exception as exc:
            errors.append(f"Could not load whiskies from master DB: {exc}")
        finally:
            try:
                if conn is not None:
                    conn.close()
            except Exception:
                pass
            if DB_PATH.exists():
                self.db_hash_after = sha256_file(DB_PATH)

    def _build_match_targets(self):
        targets = []
        for whisky in self.whiskies:
            names = [
                clean_text(whisky.get("name", "")),
                clean_text(" ".join(part for part in [whisky.get("name"), whisky.get("brand")] if part)),
            ]
            names = [name for name in dict.fromkeys(names) if name]
            for name in names:
                targets.append(
                    {
                        "whisky_id": clean_text(whisky.get("whisky_id", "")),
                        "region": normalize_text(whisky.get("region", "")),
                        "name_norm": normalize_text(name),
                        "tokens": token_set(name),
                    }
                )
        return targets

    def match(self, product_name, source_region):
        best_id = ""
        best_score = 0.0
        product_norm = normalize_text(product_name)
        region_norm = normalize_text(source_region)
        product_tokens = token_set(product_name)
        if not product_norm or not self.match_targets:
            return best_id, 0, "unmatched"

        for target in self.match_targets:
            shared_tokens = product_tokens & target["tokens"]
            if product_tokens and target["tokens"] and not shared_tokens:
                continue
            token_recall = len(shared_tokens) / max(len(product_tokens), 1)
            if token_recall < 0.25:
                continue
            matcher = difflib.SequenceMatcher(None, product_norm, target["name_norm"])
            if matcher.quick_ratio() * 100 < max(best_score - 8, 65):
                continue
            name_score = matcher.ratio() * 100

            target_region = target["region"]
            adjusted_score = name_score
            if region_norm and target_region:
                region_score = difflib.SequenceMatcher(None, region_norm, target_region).ratio() * 100
                if region_score >= 90:
                    adjusted_score += 3
                elif region_score < 55:
                    adjusted_score -= 3

            if adjusted_score > best_score:
                best_score = adjusted_score
                best_id = target["whisky_id"]

        score = max(0, min(100, int(round(best_score))))
        if score >= 92:
            status = "high_confidence_match"
        elif score >= 80:
            status = "needs_review"
        else:
            status = "unmatched"
            best_id = ""
        return best_id, score, status


def build_candidates(groups, metadata, matcher, errors):
    candidates = []
    validation_failures = []

    for product_name in sorted(groups, key=normalize_text):
        rows = groups[product_name]
        source_url = first_real_url(rows)
        if not source_url:
            validation_failures.append(f"Skipped '{product_name}' because no real Reddit review URL was found.")
            continue

        ratings = [clean_rating(row.get("Rating")) for row in rows]
        valid_ratings = [rating for rating in ratings if rating is not None]
        region = most_common_non_empty(rows, "Region") or first_non_empty(rows, "Region")
        normalized_name = normalize_text(product_name)
        meta = metadata.get(normalized_name, {})
        matched_id, match_score, match_status = matcher.match(product_name, region)

        notes = []
        if len(rows) > 1:
            notes.append(f"{len(rows) - 1} additional Reddit reviews aggregated.")
        if not valid_ratings:
            notes.append("No valid numeric ratings found in source rows.")
        if not meta:
            notes.append("No whiskysList.ts metadata match found.")

        candidate = {
            "source_system": "scotchgit",
            "source_type": "reddit_aggregate",
            "product_name": product_name,
            "normalized_product_name": normalized_name,
            "source_url": source_url,
            "reviewer": first_non_empty(rows, "Reviewer Username"),
            "rating": "",
            "price": first_non_empty(rows, "Price"),
            "region": region or meta.get("region", ""),
            "review_date": first_non_empty(rows, "Date"),
            "review_count": len(rows),
            "avg_rating": round(sum(valid_ratings) / len(valid_ratings), 2) if valid_ratings else "",
            "min_rating": min(valid_ratings) if valid_ratings else "",
            "max_rating": max(valid_ratings) if valid_ratings else "",
            "word_cloud_url": meta.get("word_cloud_url", ""),
            "map_x": meta.get("map_x", ""),
            "map_y": meta.get("map_y", ""),
            "source_verified": 0,
            "matched_master_whisky_id": matched_id,
            "match_score": match_score,
            "match_method": "difflib_name_region",
            "match_status": match_status,
            "approval_status": "pending",
            "import_recommendation": "review_before_import",
            "notes_for_review": " ".join(notes),
        }
        candidates.append(candidate)

    for index, candidate in enumerate(candidates, start=2):
        if not clean_text(candidate["product_name"]):
            validation_failures.append(f"Output row {index} has blank product_name.")
        if not clean_text(candidate["source_url"]):
            validation_failures.append(f"Output row {index} has blank source_url.")
        if "sample-" in clean_text(candidate["source_url"]).lower():
            validation_failures.append(f"Output row {index} has sample URL: {candidate['source_url']}")

    errors.extend(validation_failures)
    return candidates


def write_candidates(candidates):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_OUT_PATH.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(candidates)


def duplicate_url_conflicts(candidates):
    names_by_url = defaultdict(set)
    for candidate in candidates:
        url = clean_text(candidate.get("source_url"))
        name = normalize_text(candidate.get("normalized_product_name") or candidate.get("product_name"))
        if url and name:
            names_by_url[url].add(name)
    return {url for url, names in names_by_url.items() if len(names) > 1}


def normalize_candidate_rows(candidates):
    conflict_urls = duplicate_url_conflicts(candidates)
    normalized_rows = []
    reason_counts = Counter()

    for candidate in candidates:
        row = dict(candidate)
        url = clean_text(row.get("source_url"))
        match_status = clean_text(row.get("match_status"))
        matched_id = clean_text(row.get("matched_master_whisky_id"))
        try:
            match_score = int(float(clean_text(row.get("match_score")) or 0))
        except ValueError:
            match_score = 0

        source_url_verified = 1 if is_reddit_url(url) else 0
        duplicate_conflict = url in conflict_urls
        safe_high_match = (
            bool(matched_id)
            and match_score >= 90
            and match_status == "high_confidence_match"
            and source_url_verified == 1
            and not duplicate_conflict
        )
        master_match_verified = 1 if safe_high_match else 0

        if safe_high_match:
            normalized_match_status = "matched"
        elif match_status == "needs_review":
            normalized_match_status = "review"
        elif match_status == "unmatched":
            normalized_match_status = "unmatched"
        else:
            normalized_match_status = "review"

        if master_match_verified:
            normalized_import_recommendation = "candidate_only_high_confidence"
        elif normalized_match_status == "review":
            normalized_import_recommendation = "manual_review"
        else:
            normalized_import_recommendation = "quarantine"

        reasons = []
        if not source_url_verified:
            reasons.append("source_url_not_reddit")
        if duplicate_conflict:
            reasons.append("duplicate_source_url_conflict")
        if not matched_id:
            reasons.append("missing_matched_master_whisky_id")
        if match_status == "unmatched":
            reasons.append("match_status_unmatched")
        if match_score < 75:
            reasons.append("match_score_below_75")
        if clean_text(row.get("import_recommendation")) == "review_before_import":
            reasons.append("legacy_review_before_import")
        if "No whiskysList.ts metadata match found" in clean_text(row.get("notes_for_review")):
            reasons.append("missing_whiskyslist_metadata")
        if not clean_text(row.get("product_name")):
            reasons.append("blank_product_name")
        if not url:
            reasons.append("blank_source_url")
        if not clean_text(row.get("reviewer")):
            reasons.append("blank_reviewer")

        row["source_url_verified"] = source_url_verified
        row["master_match_verified"] = master_match_verified
        row["normalized_match_status"] = normalized_match_status
        row["normalized_import_recommendation"] = normalized_import_recommendation
        row["quarantine_reason"] = "|".join(reasons)
        reason_counts.update(reasons)
        normalized_rows.append(row)

    return normalized_rows, conflict_urls, reason_counts


def write_normalized_candidates(normalized_rows):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with NORMALIZED_CSV_OUT_PATH.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=NORMALIZED_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(normalized_rows)


def write_reports(candidates, groups, source_row_count, skipped_blank_name, metadata, errors):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    total_reviews = sum(len(rows) for rows in groups.values())
    urls_with_sample = sum(1 for row in candidates if "sample-" in row["source_url"].lower())
    blank_product_names = sum(1 for row in candidates if not clean_text(row["product_name"]))
    blank_source_urls = sum(1 for row in candidates if not clean_text(row["source_url"]))
    metadata_matches = sum(1 for row in candidates if clean_text(row["word_cloud_url"]))

    with REAL_REPORT_PATH.open("w", encoding="utf-8") as fh:
        fh.write("# ScotchGit Real Candidate Report\n\n")
        fh.write("## Source Inputs\n\n")
        fh.write(f"- scotchfile.csv rows parsed: {source_row_count}\n")
        fh.write(f"- rows skipped for blank Whisky Name: {skipped_blank_name}\n")
        fh.write(f"- grouped product names: {len(groups)}\n")
        fh.write(f"- source reviews represented after grouping: {total_reviews}\n")
        fh.write(f"- whiskysList.ts metadata entries parsed: {len(metadata)}\n\n")
        fh.write("## Output\n\n")
        fh.write(f"- candidate CSV: `{CSV_OUT_PATH.as_posix()}`\n")
        fh.write(f"- aggregate candidate rows: {len(candidates)}\n")
        fh.write(f"- metadata matches: {metadata_matches}\n")
        fh.write(f"- sample URL occurrences: {urls_with_sample}\n")
        fh.write(f"- blank product_name rows: {blank_product_names}\n")
        fh.write(f"- blank source_url rows: {blank_source_urls}\n\n")
        fh.write("## Errors And Warnings\n\n")
        if errors:
            for error in errors:
                fh.write(f"- {error}\n")
        else:
            fh.write("- None\n")

    match_counts = Counter(row["match_status"] for row in candidates)
    scores = [int(row["match_score"]) for row in candidates if str(row["match_score"]).isdigit()]
    with MATCH_REPORT_PATH.open("w", encoding="utf-8") as fh:
        fh.write("# ScotchGit Match Quality Report\n\n")
        fh.write("## Summary\n\n")
        for status in ("high_confidence_match", "needs_review", "unmatched"):
            fh.write(f"- {status}: {match_counts.get(status, 0)}\n")
        fh.write(f"- match method: difflib_name_region\n")
        fh.write(f"- master DB rows loaded: {len(set(row['matched_master_whisky_id'] for row in candidates if row['matched_master_whisky_id']))} matched ids\n")
        if scores:
            fh.write(f"- min score: {min(scores)}\n")
            fh.write(f"- max score: {max(scores)}\n")
            fh.write(f"- average score: {round(sum(scores) / len(scores), 2)}\n")
        fh.write("\n## Lowest Score Samples\n\n")
        for row in sorted(candidates, key=lambda item: int(item["match_score"]))[:20]:
            fh.write(
                f"- {row['product_name']} | score={row['match_score']} | "
                f"status={row['match_status']} | matched_id={row['matched_master_whisky_id']}\n"
            )


def write_normalization_report(normalized_rows, conflict_urls, reason_counts, matcher, errors):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    source_url_verified_count = sum(1 for row in normalized_rows if str(row["source_url_verified"]) == "1")
    master_match_verified_count = sum(1 for row in normalized_rows if str(row["master_match_verified"]) == "1")
    normalized_status_counts = Counter(row["normalized_match_status"] for row in normalized_rows)
    normalized_import_counts = Counter(row["normalized_import_recommendation"] for row in normalized_rows)
    db_changed = bool(matcher.db_hash_before and matcher.db_hash_after and matcher.db_hash_before != matcher.db_hash_after)

    with NORMALIZATION_REPORT_PATH.open("w", encoding="utf-8") as fh:
        fh.write("# ScotchGit Match Status Normalization Report\n\n")
        fh.write("## Scope\n\n")
        fh.write("- Existing candidate CSV remains backward compatible; `source_verified` is retained.\n")
        fh.write("- New fields separate source URL verification from master whisky match verification.\n")
        fh.write("- production.db was opened read-only with SQLite URI `mode=ro`.\n\n")
        fh.write("## Counts\n\n")
        fh.write(f"- total rows: {len(normalized_rows)}\n")
        fh.write(f"- source_url_verified=1: {source_url_verified_count}\n")
        fh.write(f"- source_url_verified=0: {len(normalized_rows) - source_url_verified_count}\n")
        fh.write(f"- master_match_verified=1: {master_match_verified_count}\n")
        fh.write(f"- master_match_verified=0: {len(normalized_rows) - master_match_verified_count}\n")
        fh.write(f"- duplicate source_url conflict URLs: {len(conflict_urls)}\n")
        fh.write(f"- production.db changed: {'YES' if db_changed else 'NO'}\n\n")
        fh.write("## Normalized Match Status\n\n")
        for status, count in sorted(normalized_status_counts.items()):
            fh.write(f"- {status}: {count}\n")
        fh.write("\n## Normalized Import Recommendation\n\n")
        for recommendation, count in sorted(normalized_import_counts.items()):
            fh.write(f"- {recommendation}: {count}\n")
        fh.write("\n## Quarantine Reason Distribution\n\n")
        if reason_counts:
            for reason, count in reason_counts.most_common():
                fh.write(f"- {reason}: {count}\n")
        else:
            fh.write("- None\n")
        fh.write("\n## Output\n\n")
        fh.write(f"- normalized CSV: `{NORMALIZED_CSV_OUT_PATH.as_posix()}`\n")
        fh.write("\n## Script Warnings\n\n")
        if errors:
            for error in errors:
                fh.write(f"- {error}\n")
        else:
            fh.write("- None\n")


def main():
    errors = []
    metadata = parse_whiskys_list(errors)
    groups, source_row_count, skipped_blank_name = parse_scotchfile(errors)
    matcher = MasterWhiskyMatcher(errors)
    candidates = build_candidates(groups, metadata, matcher, errors)

    try:
        write_candidates(candidates)
    except Exception as exc:
        errors.append(f"Failed to write candidate CSV: {exc}")

    normalized_rows, conflict_urls, reason_counts = normalize_candidate_rows(candidates)
    try:
        write_normalized_candidates(normalized_rows)
    except Exception as exc:
        errors.append(f"Failed to write normalized candidate CSV: {exc}")

    try:
        write_reports(candidates, groups, source_row_count, skipped_blank_name, metadata, errors)
    except Exception as exc:
        print(f"Failed to write reports: {exc}")

    try:
        write_normalization_report(normalized_rows, conflict_urls, reason_counts, matcher, errors)
    except Exception as exc:
        print(f"Failed to write normalization report: {exc}")

    print(f"ScotchGit candidates written: {len(candidates)}")
    print(f"ScotchGit normalized candidates written: {len(normalized_rows)}")
    print(f"Report written: {REAL_REPORT_PATH}")
    print(f"Match report written: {MATCH_REPORT_PATH}")
    print(f"Normalization report written: {NORMALIZATION_REPORT_PATH}")
    if errors:
        print(f"Completed with {len(errors)} warning/error entries. See report 189.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        REAL_REPORT_PATH.write_text(
            "# ScotchGit Real Candidate Report\n\n"
            "## Fatal Error\n\n"
            f"- {exc}\n",
            encoding="utf-8",
        )
        print(f"ScotchGit candidate build failed without crashing: {exc}")
