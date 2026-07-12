import csv
import difflib
import hashlib
import os
import re
import sqlite3
from collections import Counter

import pandas as pd

try:
    from rapidfuzz import fuzz

    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "output")
REPORTS_DIR = os.path.join(BASE_DIR, "output", "reports")
DB_PATH = os.path.join(BASE_DIR, "output", "import", "production.db")

INPUT_CSV = os.path.join(OUTPUT_DIR, "whiskyfun_derived_features_with_identity.csv")
REGISTRY_CSV = os.path.join(OUTPUT_DIR, "external_whisky_source_registry.csv")
PREVIEW_CSV = os.path.join(OUTPUT_DIR, "whiskyfun_derived_feature_product_match_preview.csv")
SUMMARY_CSV = os.path.join(OUTPUT_DIR, "whiskyfun_derived_feature_match_quality_summary.csv")
REPORT_MD = os.path.join(REPORTS_DIR, "315_12q_whiskyfun_product_match_preview_report.md")
GATE_TXT = os.path.join(REPORTS_DIR, "316_12q_whiskyfun_product_match_preview_gate.txt")

FORBIDDEN_OUTPUT_COLS = {"review_text", "nose", "mouth", "finish", "comments", "nmf"}
COUNT_TABLES = ["whiskies", "tasting_notes", "staging_tasting_notes", "flavor_profiles"]
PREVIEW_COLUMNS = [
    "dedupe_hash",
    "whisky_name_raw",
    "distillery",
    "source_score",
    "review_year",
    "review_date",
    "identity_status",
    "match_source",
    "matched_whisky_id",
    "matched_whisky_name",
    "matched_distillery",
    "name_match_score",
    "distillery_match",
    "conflict_flags",
    "decision",
    "decision_reason",
    "internal_source_url",
    "internal_audit_only",
]


def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR, exist_ok=True)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def connect_readonly():
    uri = f"file:{os.path.abspath(DB_PATH)}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def normalize_text(value):
    if value is None or pd.isna(value):
        return ""
    text = str(value).lower()
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def compact_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def table_columns(conn, table):
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def pick_column(columns, candidates):
    return next((col for col in candidates if col in columns), None)


def get_table_counts(conn):
    counts = {}
    for table in COUNT_TABLES:
        try:
            counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except sqlite3.Error:
            counts[table] = None
    return counts


def load_whiskies(conn):
    whisky_cols = table_columns(conn, "whiskies")
    id_col = pick_column(whisky_cols, ["whisky_id", "id"])
    name_col = pick_column(whisky_cols, ["whisky_name", "name", "product_name", "title"])
    dist_col = pick_column(whisky_cols, ["distillery", "distillery_name", "brand"])

    if not id_col or not name_col:
        raise RuntimeError("Could not find required whisky id/name columns")

    if dist_col:
        query = f"""
            SELECT {id_col} AS matched_whisky_id,
                   {name_col} AS matched_whisky_name,
                   {dist_col} AS matched_distillery
            FROM whiskies
        """
    elif "distillery_id" in whisky_cols and "distilleries" in {
        row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }:
        distillery_cols = table_columns(conn, "distilleries")
        distillery_name_col = pick_column(distillery_cols, ["distillery_name", "name", "brand"])
        if "distillery_id" in distillery_cols and distillery_name_col:
            query = f"""
                SELECT w.{id_col} AS matched_whisky_id,
                       w.{name_col} AS matched_whisky_name,
                       d.{distillery_name_col} AS matched_distillery
                FROM whiskies w
                LEFT JOIN distilleries d ON d.distillery_id = w.distillery_id
            """
        else:
            query = f"""
                SELECT {id_col} AS matched_whisky_id,
                       {name_col} AS matched_whisky_name,
                       '' AS matched_distillery
                FROM whiskies
            """
    else:
        query = f"""
            SELECT {id_col} AS matched_whisky_id,
                   {name_col} AS matched_whisky_name,
                   '' AS matched_distillery
            FROM whiskies
        """

    whiskies = pd.read_sql_query(query, conn).fillna("")
    whiskies["norm_name"] = whiskies["matched_whisky_name"].map(normalize_text)
    whiskies["norm_distillery"] = whiskies["matched_distillery"].map(normalize_text)
    return whiskies.to_dict("records")


def extract_tokens(value):
    text = str(value or "").lower()
    tokens = {}

    age = re.search(r"\b(\d{1,2})\s*(?:yo|y\.o\.|year|years|years old)\b", text)
    if not age:
        age = re.search(r"\b(\d{1,2})\s*/\s*(?:19|20)\d{2}\b", text)
    if age:
        tokens["age"] = age.group(1)

    years = re.findall(r"\b(19\d{2}|20\d{2})\b", text)
    if years:
        tokens["vintage"] = years[0]
        if len(years) > 1:
            tokens["release"] = years[-1]

    cask = re.search(r"\bcask\s*#?\s*([a-z0-9-]+)", text)
    if cask:
        tokens["cask"] = cask.group(1)

    release = re.search(r"\brelease\s*#?\s*([a-z0-9-]+)", text)
    if release:
        tokens["release"] = release.group(1)

    bottlers = [
        "signatory",
        "gordon macphail",
        "gordon & macphail",
        "cadenhead",
        "duncan taylor",
        "adelphi",
        "specialty drinks",
        "elements of islay",
        "berry bros",
        "samaroli",
        "mo or",
        "queen of the moorlands",
    ]
    found_bottlers = [b.replace("&", "and") for b in bottlers if b in text]
    if found_bottlers:
        tokens["bottler"] = "|".join(sorted(found_bottlers))

    return tokens


def score_names(left, right):
    if not left or not right:
        return 0.0
    if HAS_RAPIDFUZZ:
        return float(fuzz.token_set_ratio(left, right))
    return difflib.SequenceMatcher(None, left, right).ratio() * 100.0


def distillery_matches(source_distillery, production_distillery):
    src = normalize_text(source_distillery)
    prod = normalize_text(production_distillery)
    if not src or not prod:
        return False
    return src == prod or src in prod or prod in src or score_names(src, prod) >= 92


def conflict_flags(source_name, source_distillery, match):
    flags = []
    src_tokens = extract_tokens(source_name)
    db_tokens = extract_tokens(match["matched_whisky_name"])

    for key, flag in [
        ("age", "age_mismatch"),
        ("vintage", "vintage_mismatch"),
        ("release", "release_mismatch"),
        ("cask", "cask_mismatch"),
        ("bottler", "bottler_mismatch"),
    ]:
        if key in src_tokens and key in db_tokens and src_tokens[key] != db_tokens[key]:
            flags.append(flag)

    if source_distillery and match["matched_distillery"] and not distillery_matches(
        source_distillery, match["matched_distillery"]
    ):
        flags.append("distillery_mismatch")

    return flags


def best_match_for(row, whiskies):
    raw_name = row.get("whisky_name_raw", "")
    source_distillery = row.get("distillery", "")
    norm_name = normalize_text(raw_name)
    norm_dist = normalize_text(source_distillery)

    candidates = whiskies
    if norm_dist:
        dist_candidates = [
            w
            for w in whiskies
            if w["norm_distillery"]
            and (norm_dist in w["norm_distillery"] or w["norm_distillery"] in norm_dist)
        ]
        if dist_candidates:
            candidates = dist_candidates

    best = None
    best_score = -1.0
    for whisky in candidates:
        score = score_names(norm_name, whisky["norm_name"])
        if score > best_score:
            best = whisky
            best_score = score
            if score == 100:
                break

    return best, max(best_score, 0.0)


def decide(row, match, score, flags):
    identity_status = str(row.get("identity_status", "") or "")
    dist_match = distillery_matches(row.get("distillery", ""), match["matched_distillery"]) if match else False

    if score < 86:
        flags = list(flags)
        if "low_name_score" not in flags:
            flags.append("low_name_score")

    hard_conflicts = [f for f in flags if f != "low_name_score"]
    if hard_conflicts:
        return "REJECT_CONFLICT", ",".join(hard_conflicts), dist_match, flags

    if identity_status == "undisclosed_but_indexed":
        return "REJECT_LOW_CONFIDENCE", "identity_status undisclosed_but_indexed", dist_match, flags

    if score >= 94 and identity_status == "name_matched" and dist_match and not flags:
        return "KEEP_PRODUCT_FEATURE", "high name score, name matched, distillery matched", dist_match, flags

    if (86 <= score <= 93) or identity_status == "explicit_distillery":
        if not hard_conflicts:
            return "REVIEW_PRODUCT_FEATURE", "moderate score or explicit distillery identity", dist_match, flags

    if dist_match:
        return (
            "KEEP_DISTILLERY_FEATURE_ONLY",
            "weak product match but source distillery matched production distillery",
            dist_match,
            flags,
        )

    return "REJECT_LOW_CONFIDENCE", f"name_match_score {score:.1f}", dist_match, flags


def audit_output(df):
    full_text_leak = any(col in df.columns for col in FORBIDDEN_OUTPUT_COLS)
    source_url_col = "source_url" in df.columns
    url_columns = [
        col
        for col in df.columns
        if col != "internal_source_url"
        and df[col].astype(str).str.contains(r"https?://", case=False, regex=True, na=False).any()
    ]
    internal_audit_only_ok = (
        "internal_audit_only" in df.columns
        and df["internal_audit_only"].astype(str).str.lower().eq("true").all()
    )
    public_visibility_leak = (
        "public_visibility" in df.columns
        and df["public_visibility"].astype(str).str.lower().eq("true").any()
    )
    source_visibility_leak = bool(source_url_col or url_columns or not internal_audit_only_ok or public_visibility_leak)
    return {
        "full_text_leak": full_text_leak,
        "source_url_col": source_url_col,
        "url_columns_except_internal_source_url": "|".join(url_columns),
        "internal_audit_only_ok": internal_audit_only_ok,
        "public_visibility_leak": public_visibility_leak,
        "source_visibility_leak": source_visibility_leak,
    }


def write_missing_input_gate():
    with open(GATE_TXT, "w", encoding="utf-8") as f:
        f.write("GATE: NO_GO_MATCH_INPUT_MISSING\n")
        f.write("
Estimated API Cost: $0.00
Actual API Cost: $0.00
Local Compute Used: Yes
Fully Local Execution: Yes
")

        f.write(f"input_csv: {INPUT_CSV}\n")


def write_report(gate, stats, total_rows, db_hash_before, db_hash_after, counts_before, counts_after, audit):
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("# 315 12Q Whiskyfun Product Match Preview Report\n\n")
        f.write(f"- input_rows_processed: {total_rows}\n")
        for decision in [
            "KEEP_PRODUCT_FEATURE",
            "REVIEW_PRODUCT_FEATURE",
            "KEEP_DISTILLERY_FEATURE_ONLY",
            "REJECT_CONFLICT",
            "REJECT_LOW_CONFIDENCE",
        ]:
            f.write(f"- {decision}: {stats.get(decision, 0)}\n")
        f.write("\n## Leak Checks\n")
        f.write(f"- full_text_leak: {audit['full_text_leak']}\n")
        f.write(f"- source_url_column_in_output: {audit['source_url_col']}\n")
        f.write(
            "- url_columns_except_internal_source_url: "
            f"{audit['url_columns_except_internal_source_url'] or 'none'}\n"
        )
        f.write(f"- internal_audit_only_all_true: {audit['internal_audit_only_ok']}\n")
        f.write(f"- public_visibility_true: {audit['public_visibility_leak']}\n")
        f.write("\n## DB Safety\n")
        f.write(f"- production_db_hash_before: {db_hash_before}\n")
        f.write(f"- production_db_hash_after: {db_hash_after}\n")
        f.write(f"- production_db_changed: {db_hash_before != db_hash_after}\n")
        f.write(f"- table_counts_before: {counts_before}\n")
        f.write(f"- table_counts_after: {counts_after}\n")
        f.write(f"- table_counts_changed: {counts_before != counts_after}\n")
        f.write(f"\n## Gate\n- {gate}\n")

    with open(GATE_TXT, "w", encoding="utf-8") as f:
        f.write(f"GATE: {gate}\n")
        f.write(f"input_rows_processed: {total_rows}\n")
        f.write(f"production_db_changed: {db_hash_before != db_hash_after}\n")
        f.write(f"table_counts_changed: {counts_before != counts_after}\n")
        f.write(f"full_text_leak: {audit['full_text_leak']}\n")
        f.write(f"source_visibility_leak: {audit['source_visibility_leak']}\n")


def main():
    ensure_dirs()
    if not os.path.exists(INPUT_CSV):
        write_missing_input_gate()
        return

    db_hash_before = sha256_file(DB_PATH)
    with connect_readonly() as conn:
        counts_before = get_table_counts(conn)
        whiskies = load_whiskies(conn)

    input_df = pd.read_csv(INPUT_CSV).fillna("")
    results = []

    for _, row in input_df.iterrows():
        match, name_score = best_match_for(row, whiskies)
        if match is None:
            match = {
                "matched_whisky_id": "",
                "matched_whisky_name": "",
                "matched_distillery": "",
                "norm_name": "",
                "norm_distillery": "",
            }
            name_score = 0.0

        flags = conflict_flags(row.get("whisky_name_raw", ""), row.get("distillery", ""), match)
        decision, reason, dist_match, flags = decide(row, match, name_score, flags)

        results.append(
            {
                "dedupe_hash": row.get("dedupe_hash", ""),
                "whisky_name_raw": compact_text(row.get("whisky_name_raw", "")),
                "distillery": compact_text(row.get("distillery", "")),
                "source_score": row.get("score", ""),
                "review_year": row.get("review_year", ""),
                "review_date": row.get("review_date", ""),
                "identity_status": row.get("identity_status", ""),
                "match_source": row.get("match_source", ""),
                "matched_whisky_id": match["matched_whisky_id"],
                "matched_whisky_name": match["matched_whisky_name"],
                "matched_distillery": match["matched_distillery"],
                "name_match_score": round(name_score, 1),
                "distillery_match": bool(dist_match),
                "conflict_flags": ",".join(flags),
                "decision": decision,
                "decision_reason": reason,
                "internal_source_url": row.get("source_url", ""),
                "internal_audit_only": True,
            }
        )

    preview_df = pd.DataFrame(results, columns=PREVIEW_COLUMNS)
    preview_df.to_csv(PREVIEW_CSV, index=False)

    stats = Counter(preview_df["decision"])
    summary_rows = [
        ("input_rows_processed", len(preview_df)),
        ("rapidfuzz_available", HAS_RAPIDFUZZ),
        ("registry_present", os.path.exists(REGISTRY_CSV)),
    ]
    summary_rows.extend((decision, stats.get(decision, 0)) for decision in sorted(stats))
    with open(SUMMARY_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        writer.writerows(summary_rows)

    db_hash_after = sha256_file(DB_PATH)
    with connect_readonly() as conn:
        counts_after = get_table_counts(conn)

    audit = audit_output(preview_df)
    if db_hash_before != db_hash_after or counts_before != counts_after:
        gate = "NO_GO_DB_CHANGED"
    elif audit["full_text_leak"]:
        gate = "NO_GO_FULL_TEXT_LEAK"
    elif audit["source_visibility_leak"]:
        gate = "NO_GO_SOURCE_VISIBILITY_LEAK"
    else:
        review_rate = stats.get("REVIEW_PRODUCT_FEATURE", 0) / max(len(preview_df), 1)
        gate = "GO_WITH_HIGH_REVIEW_RATE" if review_rate > 0.2 else "GO_MATCH_PREVIEW_ONLY"

    write_report(gate, stats, len(preview_df), db_hash_before, db_hash_after, counts_before, counts_after, audit)


if __name__ == "__main__":
    main()
