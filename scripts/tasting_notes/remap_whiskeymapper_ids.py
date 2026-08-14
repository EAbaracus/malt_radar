import csv
import json
import os
import re
import sqlite3
from collections import Counter, defaultdict
from difflib import SequenceMatcher


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INPUT_CSV = os.path.join(BASE_DIR, "data", "output", "whiskeymapper_final_import_candidates_high_only.csv")
DB_PATH = os.path.join(BASE_DIR, "output", "import", "production.db")
MAP_CSV = os.path.join(BASE_DIR, "data", "output", "whiskeymapper_wdb_to_production_id_map.csv")
PREVIEW_CSV = os.path.join(BASE_DIR, "data", "output", "whiskeymapper_import_preview_remapped.csv")
REPORT_DIR = os.path.join(BASE_DIR, "output", "reports")
MAPPING_REPORT = os.path.join(REPORT_DIR, "198_whiskeymapper_id_mapping_report.md")
GATE_REPORT = os.path.join(REPORT_DIR, "199_whiskeymapper_remapped_import_gate.txt")

MAP_FIELDS = [
    "source_system",
    "old_matched_product_id",
    "production_whisky_id",
    "wm_name",
    "matched_name",
    "production_name",
    "wm_distillery",
    "matched_distillery",
    "production_brand",
    "production_region",
    "production_country",
    "wm_type",
    "production_type",
    "original_match_score",
    "remap_score",
    "remap_margin",
    "remap_status",
    "remap_reason",
]

PREVIEW_FIELDS = [
    "source_system",
    "whisky_id",
    "whisky_name",
    "wm_name",
    "wm_distillery",
    "wm_brand",
    "wm_type",
    "wm_avg_score",
    "wm_review_count",
    "wm_component_1",
    "wm_component_2",
    "wm_component_3",
    "match_score",
    "name_score",
    "token_score",
    "distillery_score",
    "score_margin",
    "remap_score",
    "remap_status",
    "source_profile",
    "converted_flavor_profile",
    "flavor_source",
    "flavor_data_confidence",
    "import_action",
    "block_reason",
]

STOPWORDS = {
    "the",
    "and",
    "of",
    "a",
    "an",
    "whisky",
    "whiskey",
    "scotch",
    "single",
    "malt",
    "year",
    "old",
    "yo",
    "yr",
    "yrs",
    "years",
    "distillery",
    "company",
    "co",
}

TYPE_ALIASES = {
    "malt": {"malt", "single malt", "scotch"},
    "bourbon": {"bourbon"},
    "rye": {"rye"},
    "blend": {"blend", "blended"},
    "grain": {"grain"},
}


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def clean(value):
    return "" if value is None else str(value).strip()


def normalize_text(value):
    value = clean(value).lower()
    value = value.replace("&", " and ")
    value = value.replace("’", "'").replace("`", "'")
    value = re.sub(r"\b(\d{1,2})\s*(?:years?\s*old|year\s*old|yo|yr|yrs|y)\b", r"\1yo", value)
    value = re.sub(r"\b(\d{1,2})\s*years?\b", r"\1yo", value)
    value = re.sub(r"\bfinished\b", "finish", value)
    value = re.sub(r"\bport finished\b", "port finish", value)
    value = re.sub(r"\bbib\b", "bottled in bond", value)
    value = re.sub(r"['’]", "", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def token_list(value):
    tokens = []
    for token in normalize_text(value).split():
        if token in STOPWORDS:
            continue
        if token.isdigit() or len(token) >= 2:
            tokens.append(token)
    return tokens


def token_set(*values):
    out = set()
    for value in values:
        out.update(token_list(value))
    return out


def ratio(left, right):
    left_norm = normalize_text(left)
    right_norm = normalize_text(right)
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def ratio_norm(left_norm, right_norm):
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def token_overlap(left_tokens, right_tokens):
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = left_tokens & right_tokens
    precision = len(overlap) / len(left_tokens)
    recall = len(overlap) / len(right_tokens)
    if precision + recall == 0:
        return 0.0
    return (2 * precision * recall) / (precision + recall)


def age_tokens(*values):
    ages = set()
    for value in values:
        for match in re.finditer(r"\b(\d{1,2})yo\b", normalize_text(value)):
            ages.add(match.group(1))
        for match in re.finditer(r"\b(\d{1,2})\b", normalize_text(value)):
            number = int(match.group(1))
            if 3 <= number <= 50:
                ages.add(str(number))
    return ages


def normalize_type(value):
    value_norm = normalize_text(value)
    for canonical, aliases in TYPE_ALIASES.items():
        if any(alias in value_norm for alias in aliases):
            return canonical
    return value_norm


def load_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT whisky_id, name, original_name, brand, distillery_id, region,
                   country, type, age, age_statement
            FROM whiskies
            """
        )
        whiskies = [dict(row) for row in cur.fetchall()]
        cur.execute("SELECT whisky_id FROM flavor_profiles")
        existing_profiles = {row[0] for row in cur.fetchall()}
        table_counts = {}
        for table in ("whiskies", "flavor_profiles", "tasting_notes", "staging_tasting_notes"):
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            table_counts[table] = cur.fetchone()[0]
        return whiskies, existing_profiles, table_counts
    finally:
        conn.close()


def prepare_production_rows(whiskies):
    prepared = []
    for row in whiskies:
        names = [row.get("name"), row.get("original_name")]
        if row.get("brand") and row.get("name"):
            names.append(f"{row.get('brand')} {row.get('name')}")
        row["_names"] = [name for name in names if clean(name)]
        row["_name_norms"] = [normalize_text(name) for name in row["_names"]]
        row["_name_tokens"] = token_set(*row["_names"])
        row["_brand_tokens"] = token_set(row.get("brand"), row.get("name"))
        row["_age_tokens"] = age_tokens(row.get("name"), row.get("original_name"), row.get("age_statement"))
        if row.get("age") not in (None, ""):
            try:
                row["_age_tokens"].add(str(int(float(row["age"]))))
            except ValueError:
                pass
        row["_type_norm"] = normalize_type(row.get("type"))
        prepared.append(row)
    return prepared


def build_token_index(production_rows):
    index = defaultdict(set)
    for row_index, row in enumerate(production_rows):
        for token in row["_name_tokens"] | row["_brand_tokens"] | row["_age_tokens"]:
            index[token].add(row_index)
    return index


def prepare_source_row(row):
    source_names = [
        row.get("matched_name", ""),
        row.get("wm_name", ""),
        f"{row.get('wm_distillery', '')} {row.get('wm_name', '')}",
        f"{row.get('wm_brand', '')} {row.get('wm_name', '')}",
    ]
    row = dict(row)
    row["_source_name_norms"] = [normalize_text(name) for name in source_names if clean(name)]
    row["_source_tokens"] = token_set(
        row.get("matched_name"),
        row.get("wm_name"),
        row.get("wm_distillery"),
        row.get("wm_brand"),
    )
    row["_brand_tokens"] = token_set(row.get("wm_distillery"), row.get("wm_brand"), row.get("matched_distillery"))
    row["_age_tokens"] = age_tokens(row.get("matched_name"), row.get("wm_name"))
    row["_type_norm"] = normalize_type(row.get("wm_type") or row.get("matched_category"))
    row["_country_norm"] = normalize_text(row.get("matched_country"))
    row["_matched_name_norm"] = normalize_text(row.get("matched_name"))
    return row


def score_candidate(source_row, production_row):
    production_name_norms = production_row["_name_norms"] or [normalize_text(production_row.get("name", ""))]

    name_score = max(
        ratio_norm(source_name, production_name)
        for source_name in source_row["_source_name_norms"]
        for production_name in production_name_norms
    )
    token_score = token_overlap(source_row["_source_tokens"], production_row["_name_tokens"])
    brand_score = token_overlap(source_row["_brand_tokens"], production_row["_brand_tokens"])
    age_score = (
        1.0
        if source_row["_age_tokens"]
        and production_row["_age_tokens"]
        and source_row["_age_tokens"] & production_row["_age_tokens"]
        else 0.0
    )
    type_score = 1.0 if source_row["_type_norm"] and source_row["_type_norm"] == production_row["_type_norm"] else 0.0
    production_country = normalize_text(production_row.get("country"))
    country_score = 1.0 if source_row["_country_norm"] and production_country and source_row["_country_norm"] == production_country else 0.0

    remap_score = (
        (name_score * 0.58)
        + (token_score * 0.25)
        + (brand_score * 0.09)
        + (age_score * 0.04)
        + (type_score * 0.03)
        + (country_score * 0.01)
    )

    matched_norm = source_row["_matched_name_norm"]
    for production_norm in production_name_norms:
        if matched_norm and production_norm and matched_norm == production_norm:
            remap_score = max(remap_score, 0.99)
        elif matched_norm and production_norm and (matched_norm in production_norm or production_norm in matched_norm):
            remap_score = max(remap_score, 0.94)

    return min(remap_score, 1.0), {
        "name": name_score,
        "token": token_score,
        "brand": brand_score,
        "age": age_score,
        "type": type_score,
        "country": country_score,
    }


def find_best_mapping(source_row, production_rows, token_index):
    candidate_indexes = set()
    for token in source_row["_source_tokens"] | source_row["_brand_tokens"] | source_row["_age_tokens"]:
        candidate_indexes.update(token_index.get(token, set()))

    if not candidate_indexes:
        candidate_indexes = set(range(len(production_rows)))

    scored = []
    for index in candidate_indexes:
        production_row = production_rows[index]
        score, parts = score_candidate(source_row, production_row)
        scored.append((score, production_row, parts))
    scored.sort(key=lambda item: item[0], reverse=True)
    best = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0
    margin = best[0] - second_score
    return best[0], margin, best[1], best[2]


def remap_status(score, margin):
    if score >= 0.92 and margin >= 0.04:
        return "remap_high_confidence"
    if score >= 0.85:
        return "remap_needs_review"
    return "remap_unmatched"


def component_json(row):
    return json.dumps(
        {
            "component_1": row.get("wm_component_1", ""),
            "component_2": row.get("wm_component_2", ""),
            "component_3": row.get("wm_component_3", ""),
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def build_mapping_rows(source_rows, production_rows, token_index):
    mapping_rows = []
    enriched = []
    for raw_row in source_rows:
        row = prepare_source_row(raw_row)
        score, margin, production, parts = find_best_mapping(row, production_rows, token_index)
        status = remap_status(score, margin)
        reason = (
            f"name={parts['name']:.3f}; token={parts['token']:.3f}; "
            f"brand={parts['brand']:.3f}; age={parts['age']:.3f}; "
            f"type={parts['type']:.3f}; country={parts['country']:.3f}; margin={margin:.3f}"
        )
        mapping = {
            "source_system": "whiskeymapper",
            "old_matched_product_id": row.get("matched_product_id", ""),
            "production_whisky_id": production.get("whisky_id", ""),
            "wm_name": row.get("wm_name", ""),
            "matched_name": row.get("matched_name", ""),
            "production_name": production.get("name", ""),
            "wm_distillery": row.get("wm_distillery", ""),
            "matched_distillery": row.get("matched_distillery", ""),
            "production_brand": production.get("brand", ""),
            "production_region": production.get("region", ""),
            "production_country": production.get("country", ""),
            "wm_type": row.get("wm_type", ""),
            "production_type": production.get("type", ""),
            "original_match_score": row.get("match_score", ""),
            "remap_score": f"{score:.4f}",
            "remap_margin": f"{margin:.4f}",
            "remap_status": status,
            "remap_reason": reason,
        }
        mapping_rows.append(mapping)
        enriched.append((row, mapping, production))
    return mapping_rows, enriched


def duplicate_losers(enriched_rows):
    grouped = defaultdict(list)
    for index, (_, mapping, _) in enumerate(enriched_rows):
        production_id = mapping["production_whisky_id"]
        if production_id:
            grouped[production_id].append(index)

    loser_indexes = set()
    duplicate_ids = {}
    for production_id, indexes in grouped.items():
        if len(indexes) <= 1:
            continue
        duplicate_ids[production_id] = len(indexes)

        def sort_key(index):
            _, mapping, _ = enriched_rows[index]
            return float(mapping["remap_score"]), float(mapping["remap_margin"])

        winner = max(indexes, key=sort_key)
        loser_indexes.update(index for index in indexes if index != winner)
    return duplicate_ids, loser_indexes


def build_preview_rows(enriched_rows, existing_profiles, loser_indexes):
    preview_rows = []
    for index, (source, mapping, production) in enumerate(enriched_rows):
        production_id = mapping["production_whisky_id"]
        components = [
            clean(source.get("wm_component_1")),
            clean(source.get("wm_component_2")),
            clean(source.get("wm_component_3")),
        ]
        reasons = []

        if any(not component for component in components):
            reasons.append("missing_profile_components")

        status = mapping["remap_status"]
        if index in loser_indexes:
            import_action = "block_duplicate_remap"
            reasons.append("duplicate_remap_loser")
        elif status == "remap_needs_review":
            import_action = "block_needs_review"
            reasons.append("remap_needs_review")
        elif status == "remap_unmatched":
            import_action = "block_unmatched"
            reasons.append("remap_unmatched")
        elif any(not component for component in components):
            import_action = "block_missing_profile_components"
        elif production_id in existing_profiles:
            import_action = "skip_existing_profile"
            reasons.append("whisky_id_already_has_flavor_profile")
        else:
            import_action = "import_candidate"

        source_profile = component_json(source)
        preview_rows.append({
            "source_system": "whiskeymapper",
            "whisky_id": production_id,
            "whisky_name": production.get("name", ""),
            "wm_name": source.get("wm_name", ""),
            "wm_distillery": source.get("wm_distillery", ""),
            "wm_brand": source.get("wm_brand", ""),
            "wm_type": source.get("wm_type", ""),
            "wm_avg_score": source.get("wm_avg_score", ""),
            "wm_review_count": source.get("wm_review_count", ""),
            "wm_component_1": source.get("wm_component_1", ""),
            "wm_component_2": source.get("wm_component_2", ""),
            "wm_component_3": source.get("wm_component_3", ""),
            "match_score": source.get("match_score", ""),
            "name_score": source.get("name_score", ""),
            "token_score": source.get("token_score", ""),
            "distillery_score": source.get("distillery_score", ""),
            "score_margin": source.get("score_margin", ""),
            "remap_score": mapping["remap_score"],
            "remap_status": status,
            "source_profile": source_profile,
            "converted_flavor_profile": source_profile,
            "flavor_source": "whiskeymapper",
            "flavor_data_confidence": "medium",
            "import_action": import_action,
            "block_reason": "; ".join(reasons),
        })
    return preview_rows


def write_csv(path, fields, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_reports(source_rows, mapping_rows, preview_rows, table_counts, duplicate_ids):
    os.makedirs(REPORT_DIR, exist_ok=True)
    status_counts = Counter(row["remap_status"] for row in mapping_rows)
    action_counts = Counter(row["import_action"] for row in preview_rows)
    block_missing_fk = sum(1 for row in preview_rows if not row["whisky_id"])

    duplicate_blocked = action_counts["block_duplicate_remap"]
    needs_review_or_unmatched = action_counts["block_needs_review"] + action_counts["block_unmatched"]
    if action_counts["import_candidate"] == 0:
        gate = "NO-GO"
    elif action_counts["import_candidate"] >= 50 and (duplicate_blocked > 50 or needs_review_or_unmatched > 75):
        gate = "FIX_REQUIRED"
    elif action_counts["import_candidate"] >= 250 and block_missing_fk == 0:
        gate = "GO"
    elif action_counts["import_candidate"] >= 50:
        gate = "PARTIAL"
    else:
        gate = "NO-GO"

    report = [
        "# Whiskey Mapper WDB to Production ID Mapping Report",
        "",
        "## Safety",
        "- Production DB write: NO",
        "- `whiskies` write: NO",
        "- `flavor_profiles` write: NO",
        "- Outputs are mapping and dry-run preview CSVs only.",
        "",
        "## Inputs",
        f"- Whiskey Mapper candidates: `{os.path.relpath(INPUT_CSV, BASE_DIR)}`",
        f"- Production DB: `{os.path.relpath(DB_PATH, BASE_DIR)}`",
        "",
        "## Existing DB Counts",
    ]
    for table in ("whiskies", "flavor_profiles", "tasting_notes", "staging_tasting_notes"):
        report.append(f"- {table}: {table_counts.get(table, 0)}")
    report.extend([
        "",
        "## Remap Status Counts",
        f"- remap_high_confidence: {status_counts['remap_high_confidence']}",
        f"- remap_needs_review: {status_counts['remap_needs_review']}",
        f"- remap_unmatched: {status_counts['remap_unmatched']}",
        f"- remap_duplicate: {status_counts['remap_duplicate']}",
        f"- duplicate production whisky_id values: {len(duplicate_ids)}",
        f"- duplicate remap rows blocked: {duplicate_blocked}",
        "",
        "## Import Preview Actions",
    ])
    for action in (
        "import_candidate",
        "skip_existing_profile",
        "block_needs_review",
        "block_unmatched",
        "block_duplicate_remap",
        "block_missing_profile_components",
    ):
        report.append(f"- {action}: {action_counts[action]}")
    report.extend([
        "",
        "## Outputs",
        f"- Mapping CSV: `{os.path.relpath(MAP_CSV, BASE_DIR)}`",
        f"- Remapped preview CSV: `{os.path.relpath(PREVIEW_CSV, BASE_DIR)}`",
        "",
        "## Gate",
        f"- Decision: {gate}",
        f"- Source rows: {len(source_rows)}",
        f"- Import candidates: {action_counts['import_candidate']}",
        f"- block_missing_fk: {block_missing_fk}",
        "",
        "## Duplicate Production IDs",
    ])
    if duplicate_ids:
        for production_id, count in sorted(duplicate_ids.items()):
            report.append(f"- {production_id}: {count} Whiskey Mapper rows")
    else:
        report.append("None")
    with open(MAPPING_REPORT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(report) + "\n")
        handle.write(
            "\n"
            "Estimated API Cost: $0.00\n"
            "Actual API Cost: $0.00\n"
            "Local Compute Used: Yes\n"
            "Fully Local Execution: Yes\n"
        )


    gate_lines = [
        "11D-WM-IDMAP Whiskey Mapper Remapped Import Gate",
        "=================================================",
        f"Decision: {gate}",
        f"Source rows: {len(source_rows)}",
        f"Mapping rows: {len(mapping_rows)}",
        f"Preview rows: {len(preview_rows)}",
        f"Import candidates: {action_counts['import_candidate']}",
        f"Skip existing profiles: {action_counts['skip_existing_profile']}",
        f"Block missing FK: {block_missing_fk}",
        f"Block needs review: {action_counts['block_needs_review']}",
        f"Block unmatched: {action_counts['block_unmatched']}",
        f"Block duplicate remap: {action_counts['block_duplicate_remap']}",
        f"Duplicate production whisky_id values: {len(duplicate_ids)}",
    ]
    with open(GATE_REPORT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(gate_lines) + "\n")
    return gate, action_counts, status_counts


def main():
    source_rows = read_csv(INPUT_CSV)
    whiskies, existing_profiles, table_counts = load_db()
    production_rows = prepare_production_rows(whiskies)
    token_index = build_token_index(production_rows)
    mapping_rows, enriched_rows = build_mapping_rows(source_rows, production_rows, token_index)
    duplicate_ids, loser_indexes = duplicate_losers(enriched_rows)
    for index in loser_indexes:
        mapping_rows[index]["remap_status"] = "remap_duplicate"
        mapping_rows[index]["remap_reason"] += "; duplicate_remap_loser"
    preview_rows = build_preview_rows(enriched_rows, existing_profiles, loser_indexes)

    write_csv(MAP_CSV, MAP_FIELDS, mapping_rows)
    write_csv(PREVIEW_CSV, PREVIEW_FIELDS, preview_rows)
    gate, action_counts, status_counts = write_reports(source_rows, mapping_rows, preview_rows, table_counts, duplicate_ids)

    print(f"Source rows: {len(source_rows)}")
    print(f"Mapping rows: {len(mapping_rows)}")
    print(f"Preview rows: {len(preview_rows)}")
    print(f"remap_high_confidence: {status_counts['remap_high_confidence']}")
    print(f"remap_duplicate: {status_counts['remap_duplicate']}")
    print(f"import_candidate: {action_counts['import_candidate']}")
    print(f"Decision: {gate}")
    print(MAP_CSV)
    print(PREVIEW_CSV)


if __name__ == "__main__":
    main()
