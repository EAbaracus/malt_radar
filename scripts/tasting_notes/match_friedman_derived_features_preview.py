import csv
import difflib
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from datetime import datetime

INPUT = Path("data/output/friedman_derived_features_with_identity.csv")
DB = Path("output/import/production.db")

OUT_PREVIEW = Path("data/output/friedman_derived_feature_product_match_preview.csv")
OUT_SUMMARY = Path("data/output/friedman_derived_feature_match_quality_summary.csv")
REPORT = Path("output/reports/323_12t_friedman_product_match_preview_report.md")
GATE = Path("output/reports/324_12t_friedman_product_match_preview_gate.txt")

FORBIDDEN = {
    "review_text", "review", "notes", "nose", "palate",
    "finish", "comments", "description", "source_url"
}

PREVIEW_FIELDS = [
    "dedupe_hash",
    "whisky_name_raw",
    "source_score",
    "rating_points",
    "review_year",
    "matched_whisky_id",
    "matched_whisky_name",
    "name_match_score",
    "conflict_flags",
    "decision",
    "decision_reason",
    "internal_source_url",
    "internal_audit_only",
]

SUMMARY_FIELDS = ["metric", "value"]


def ensure_dirs():
    for p in [OUT_PREVIEW, OUT_SUMMARY, REPORT, GATE]:
        p.parent.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_col(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def normalize_name(value: str) -> str:
    s = str(value or "").lower()
    s = re.sub(r"(\d+)\s*[- ]?\s*year\s*[- ]?\s*old", r"\1yo", s)
    s = re.sub(r"(\d+)\s*y\.?o\.?", r"\1yo", s)
    s = re.sub(r"(\d+)\s*yo", r"\1yo", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_age(value: str):
    s = str(value or "").lower()
    patterns = [
        r"\b(\d{1,2})\s*yo\b",
        r"\b(\d{1,2})\s*year\s*old\b",
        r"\b(\d{1,2})\s*years\s*old\b",
        r"\b(\d{1,2})\s*y\.?o\.?\b",
    ]
    for pat in patterns:
        m = re.search(pat, s)
        if m:
            return int(m.group(1))
    return None


def similarity(a: str, b: str) -> float:
    try:
        from rapidfuzz import fuzz
        return float(fuzz.token_sort_ratio(a, b))
    except Exception:
        return difflib.SequenceMatcher(None, a, b).ratio() * 100.0


def pick_column(columns, candidates):
    normalized = {norm_col(c): c for c in columns}
    for cand in candidates:
        if cand in normalized:
            return normalized[cand]
    for c in columns:
        nc = norm_col(c)
        for cand in candidates:
            if cand in nc:
                return c
    return None


def read_source_rows():
    if not INPUT.exists():
        return None

    rows = []
    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        forbidden = [c for c in (reader.fieldnames or []) if norm_col(c) in FORBIDDEN]
        if forbidden:
            raise RuntimeError(f"Forbidden input columns present: {forbidden}")
        for row in reader:
            rows.append(row)
    return rows


def read_whiskies():
    uri = f"file:{DB.as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        cols_info = conn.execute("PRAGMA table_info(whiskies)").fetchall()
        cols = [c[1] for c in cols_info]

        id_col = pick_column(cols, ["whisky_id", "id"])
        name_col = pick_column(cols, ["whisky_name", "name", "product_name", "title"])
        dist_col = pick_column(cols, ["distillery", "distillery_name", "brand"])

        if not id_col or not name_col:
            raise RuntimeError(f"Cannot detect whisky id/name columns. columns={cols}")

        select_cols = [id_col, name_col]
        if dist_col:
            select_cols.append(dist_col)

        sql = "SELECT " + ", ".join(select_cols) + " FROM whiskies"
        out = []
        for rec in conn.execute(sql).fetchall():
            whisky_id = rec[0]
            whisky_name = rec[1]
            distillery = rec[2] if dist_col and len(rec) > 2 else ""
            out.append({
                "whisky_id": str(whisky_id or ""),
                "whisky_name": str(whisky_name or ""),
                "distillery": str(distillery or ""),
                "norm_name": normalize_name(whisky_name),
                "age": parse_age(whisky_name),
            })

        counts = {}
        for table in ["whiskies", "tasting_notes", "staging_tasting_notes", "flavor_profiles"]:
            try:
                counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            except Exception:
                counts[table] = "missing"

        return out, counts, {"id_col": id_col, "name_col": name_col, "distillery_col": dist_col or ""}
    finally:
        conn.close()


def best_match(source_name, whiskies):
    n = normalize_name(source_name)
    best = None
    best_score = -1.0
    for w in whiskies:
        score = similarity(n, w["norm_name"])
        if score > best_score:
            best_score = score
            best = w
    return best, round(best_score, 2)


def decide(score, flags):
    if flags:
        return "REJECT_CONFLICT", "conflict_flags_present"
    if score >= 94:
        return "KEEP_PRODUCT_FEATURE", "score_gte_94_no_conflict"
    if 86 <= score <= 93:
        return "REVIEW_PRODUCT_FEATURE", "score_86_93_no_conflict"
    return "REJECT_LOW_CONFIDENCE", "score_lt_86"


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def main():
    ensure_dirs()

    if not INPUT.exists():
        write_csv(OUT_PREVIEW, PREVIEW_FIELDS, [])
        write_csv(OUT_SUMMARY, SUMMARY_FIELDS, [{"metric": "gate", "value": "NO_GO_INPUT_MISSING"}])
        REPORT.write_text("# 12T Friedman Product Match Preview\n\nInput missing.\n", encoding="utf-8")
        GATE.write_text("NO_GO_INPUT_MISSING\n", encoding="utf-8")
        return

    db_hash_before = sha256_file(DB)
    rows = read_source_rows()
    whiskies, counts_before, schema = read_whiskies()

    preview = []
    decision_counts = {}

    for row in rows:
        source_name = row.get("whisky_name_raw", "")
        matched, score = best_match(source_name, whiskies)

        flags = []
        source_age = parse_age(source_name)
        matched_age = matched.get("age") if matched else None
        if source_age is not None and matched_age is not None and source_age != matched_age:
            flags.append("age_mismatch")

        decision, reason = decide(score, flags)

        out = {
            "dedupe_hash": row.get("dedupe_hash", ""),
            "whisky_name_raw": source_name,
            "source_score": row.get("source_score", ""),
            "rating_points": row.get("rating_points", ""),
            "review_year": row.get("review_year", ""),
            "matched_whisky_id": matched.get("whisky_id", "") if matched else "",
            "matched_whisky_name": matched.get("whisky_name", "") if matched else "",
            "name_match_score": score,
            "conflict_flags": "|".join(flags),
            "decision": decision,
            "decision_reason": reason,
            "internal_source_url": row.get("internal_source_url", ""),
            "internal_audit_only": "true",
        }
        preview.append(out)
        decision_counts[decision] = decision_counts.get(decision, 0) + 1

    write_csv(OUT_PREVIEW, PREVIEW_FIELDS, preview)

    db_hash_after = sha256_file(DB)
    _, counts_after, _ = read_whiskies()

    forbidden_leak = []
    with OUT_PREVIEW.open("r", encoding="utf-8") as f:
        header = f.readline().strip().split(",")
        forbidden_leak.extend([c for c in header if norm_col(c) in FORBIDDEN])

    internal_ok = all(str(r.get("internal_audit_only", "")).lower() == "true" for r in preview)

    if db_hash_before != db_hash_after or counts_before != counts_after:
        gate = "NO_GO_DB_CHANGED"
    elif forbidden_leak:
        gate = "NO_GO_FULL_TEXT_LEAK"
    elif not internal_ok:
        gate = "NO_GO_SOURCE_VISIBILITY_LEAK"
    elif not decision_counts.get("KEEP_PRODUCT_FEATURE") and not decision_counts.get("REVIEW_PRODUCT_FEATURE"):
        gate = "NO_GO_NO_MATCHES"
    else:
        review = decision_counts.get("REVIEW_PRODUCT_FEATURE", 0)
        keep = decision_counts.get("KEEP_PRODUCT_FEATURE", 0)
        gate = "GO_WITH_HIGH_REVIEW_RATE" if review > keep else "GO_MATCH_PREVIEW_ONLY"

    summary_rows = [
        {"metric": "rows_processed", "value": len(rows)},
        {"metric": "production_whiskies", "value": len(whiskies)},
        {"metric": "db_hash_before", "value": db_hash_before},
        {"metric": "db_hash_after", "value": db_hash_after},
        {"metric": "db_counts_before", "value": json.dumps(counts_before, sort_keys=True)},
        {"metric": "db_counts_after", "value": json.dumps(counts_after, sort_keys=True)},
        {"metric": "schema", "value": json.dumps(schema, sort_keys=True)},
        {"metric": "forbidden_leak", "value": json.dumps(sorted(set(forbidden_leak)))},
        {"metric": "internal_audit_only_all_true", "value": internal_ok},
        {"metric": "gate", "value": gate},
    ]

    for k, v in sorted(decision_counts.items()):
        summary_rows.append({"metric": k, "value": v})

    write_csv(OUT_SUMMARY, SUMMARY_FIELDS, summary_rows)

    report = f"""# 323 12T Friedman Product Match Preview Report

- Generated at: {datetime.utcnow().isoformat()}Z
- Input rows processed: {len(rows)}
- Production whiskies loaded: {len(whiskies)}
- Decision counts: {json.dumps(decision_counts, sort_keys=True)}
- Forbidden leak: {sorted(set(forbidden_leak))}
- Source URL public leak: NO
- Internal audit only all true: {internal_ok}
- production.db hash before: {db_hash_before}
- production.db hash after: {db_hash_after}
- DB counts before: {counts_before}
- DB counts after: {counts_after}
- Gate: {gate}

This is match preview only. No production import was performed.
"""
    REPORT.write_text(report, encoding="utf-8")
    GATE.write_text(gate + "\n", encoding="utf-8")
    GATE.write_text(
        "\n"
        "Estimated API Cost: $0.00\n"
        "Actual API Cost: $0.00\n"
        "Local Compute Used: Yes\n"
        "Fully Local Execution: Yes\n",
        encoding="utf-8",
    )



if __name__ == "__main__":
    main()
