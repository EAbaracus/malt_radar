import csv
import json
import os
import sqlite3
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INPUT_CSV = os.path.join(BASE_DIR, "data", "output", "whiskeymapper_final_import_candidates_high_only.csv")
DB_PATH = os.path.join(BASE_DIR, "output", "import", "production.db")
PREVIEW_CSV = os.path.join(BASE_DIR, "data", "output", "whiskeymapper_import_preview.csv")
REPORT_DIR = os.path.join(BASE_DIR, "output", "reports")
DRY_RUN_REPORT = os.path.join(REPORT_DIR, "191_whiskeymapper_import_dry_run_report.md")
CONFLICT_REPORT = os.path.join(REPORT_DIR, "192_whiskeymapper_existing_profile_conflict_report.md")
GATE_REPORT = os.path.join(REPORT_DIR, "193_whiskeymapper_import_go_no_go_gate.txt")

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
    "source_profile",
    "converted_flavor_profile",
    "flavor_source",
    "flavor_data_confidence",
    "import_action",
    "block_reason",
]


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_decimal(value):
    value = "" if value is None else str(value).strip()
    if value == "":
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def load_db_sets():
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("SELECT whisky_id, name FROM whiskies")
        whiskies = {row[0]: row[1] for row in cur.fetchall()}
        cur.execute("SELECT whisky_id FROM flavor_profiles")
        existing_profiles = {row[0] for row in cur.fetchall()}
        table_counts = {}
        for table in ("whiskies", "flavor_profiles", "tasting_notes", "staging_tasting_notes"):
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            table_counts[table] = cur.fetchone()[0]
        return whiskies, existing_profiles, table_counts
    finally:
        conn.close()


def component_json(row):
    payload = {
        "component_1": row.get("wm_component_1", ""),
        "component_2": row.get("wm_component_2", ""),
        "component_3": row.get("wm_component_3", ""),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def is_safe_final_gate(row):
    return (row.get("final_gate") or "").strip() == "IMPORT_CANDIDATE_HIGH_ONLY"


def choose_duplicate_winners(rows):
    grouped = defaultdict(list)
    for index, row in enumerate(rows):
        grouped[(row.get("matched_product_id") or "").strip()].append((index, row))

    duplicate_ids = {key for key, values in grouped.items() if key and len(values) > 1}
    winners = set()
    for key, values in grouped.items():
        if key not in duplicate_ids:
            continue

        def sort_key(item):
            _, row = item
            match_score = parse_decimal(row.get("match_score")) or Decimal("-1")
            score_margin = parse_decimal(row.get("score_margin")) or Decimal("-1")
            return match_score, score_margin

        winner_index, _ = max(values, key=sort_key)
        winners.add(winner_index)
    return duplicate_ids, winners


def build_preview(rows, whiskies, existing_profiles, duplicate_ids, duplicate_winners):
    preview_rows = []
    counters = Counter()

    for index, row in enumerate(rows):
        whisky_id = (row.get("matched_product_id") or "").strip()
        match_score = parse_decimal(row.get("match_score"))
        avg_score = parse_decimal(row.get("wm_avg_score"))
        review_count = parse_decimal(row.get("wm_review_count"))
        components = [
            (row.get("wm_component_1") or "").strip(),
            (row.get("wm_component_2") or "").strip(),
            (row.get("wm_component_3") or "").strip(),
        ]

        reasons = []
        if not whisky_id:
            reasons.append("missing_matched_product_id")
        if whisky_id and whisky_id not in whiskies:
            reasons.append("matched_product_id_not_in_whiskies")
        if match_score is None:
            reasons.append("match_score_not_parseable")
        elif match_score < Decimal("0.92"):
            reasons.append("match_score_below_0.92")
        if not is_safe_final_gate(row):
            reasons.append("final_gate_not_import_candidate_high_only")
        if any(component == "" for component in components):
            reasons.append("missing_profile_components")
        if avg_score is None:
            reasons.append("wm_avg_score_not_parseable")
        if review_count is None:
            reasons.append("wm_review_count_not_parseable")
        if whisky_id in duplicate_ids and index not in duplicate_winners:
            reasons.append("duplicate_matched_product_id_loser")

        if whisky_id in existing_profiles:
            import_action = "skip_existing_profile"
        elif whisky_id and whisky_id not in whiskies:
            import_action = "block_missing_fk"
        elif match_score is None or match_score < Decimal("0.92"):
            import_action = "block_low_match_score"
        elif whisky_id in duplicate_ids and index not in duplicate_winners:
            import_action = "block_duplicate"
        elif any(component == "" for component in components):
            import_action = "block_missing_profile_components"
        elif not whisky_id:
            import_action = "block_missing_fk"
        elif not is_safe_final_gate(row) or avg_score is None or review_count is None:
            import_action = "block_invalid_source_row"
        else:
            import_action = "import_candidate"

        if import_action == "skip_existing_profile" and not reasons:
            reasons.append("whisky_id_already_has_flavor_profile")

        source_profile = component_json(row)
        converted_flavor_profile = source_profile

        preview_rows.append({
            "source_system": "whiskeymapper",
            "whisky_id": whisky_id,
            "whisky_name": whiskies.get(whisky_id, row.get("matched_name", "")),
            "wm_name": row.get("wm_name", ""),
            "wm_distillery": row.get("wm_distillery", ""),
            "wm_brand": row.get("wm_brand", ""),
            "wm_type": row.get("wm_type", ""),
            "wm_avg_score": row.get("wm_avg_score", ""),
            "wm_review_count": row.get("wm_review_count", ""),
            "wm_component_1": row.get("wm_component_1", ""),
            "wm_component_2": row.get("wm_component_2", ""),
            "wm_component_3": row.get("wm_component_3", ""),
            "match_score": row.get("match_score", ""),
            "name_score": row.get("name_score", ""),
            "token_score": row.get("token_score", ""),
            "distillery_score": row.get("distillery_score", ""),
            "score_margin": row.get("score_margin", ""),
            "source_profile": source_profile,
            "converted_flavor_profile": converted_flavor_profile,
            "flavor_source": "whiskeymapper",
            "flavor_data_confidence": "medium",
            "import_action": import_action,
            "block_reason": "; ".join(reasons),
        })
        counters[import_action] += 1
        for reason in reasons:
            counters[reason] += 1

    return preview_rows, counters


def write_preview(rows):
    os.makedirs(os.path.dirname(PREVIEW_CSV), exist_ok=True)
    with open(PREVIEW_CSV, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PREVIEW_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def write_reports(input_rows, preview_rows, counters, table_counts, duplicate_ids):
    os.makedirs(REPORT_DIR, exist_ok=True)
    action_counts = Counter(row["import_action"] for row in preview_rows)
    fk_missing = counters["matched_product_id_not_in_whiskies"] + counters["missing_matched_product_id"]
    low_score_in_import = sum(
        1
        for row in preview_rows
        if row["import_action"] == "import_candidate"
        and (parse_decimal(row["match_score"]) is None or parse_decimal(row["match_score"]) < Decimal("0.92"))
    )
    critical_duplicate = len(duplicate_ids)

    if not input_rows or action_counts["import_candidate"] == 0:
        gate = "NO-GO"
    elif fk_missing or low_score_in_import or critical_duplicate:
        gate = "FIX_REQUIRED"
    elif action_counts["import_candidate"] >= 250:
        gate = "GO"
    elif action_counts["import_candidate"] >= 50:
        gate = "PARTIAL"
    else:
        gate = "NO-GO"

    report = [
        "# Whiskey Mapper Import Dry-Run Report",
        "",
        "## Safety",
        "- Production DB write: NO",
        "- `whiskies` write: NO",
        "- `flavor_profiles` write: NO",
        "- `tasting_notes` write: NO",
        "",
        "## Inputs",
        f"- Candidate CSV: `{os.path.relpath(INPUT_CSV, BASE_DIR)}`",
        f"- Production DB: `{os.path.relpath(DB_PATH, BASE_DIR)}`",
        "",
        "## Existing DB Counts",
    ]
    for table in ("whiskies", "flavor_profiles", "tasting_notes", "staging_tasting_notes"):
        report.append(f"- {table}: {table_counts.get(table, 0)}")
    report.extend([
        "",
        "## Candidate Checks",
        f"- CSV rows: {len(input_rows)}",
        f"- Empty matched_product_id: {counters['missing_matched_product_id']}",
        f"- matched_product_id missing from whiskies: {counters['matched_product_id_not_in_whiskies']}",
        f"- Duplicate matched_product_id values: {len(duplicate_ids)}",
        f"- Existing flavor profile conflicts: {action_counts['skip_existing_profile']}",
        f"- Low match score rows: {counters['match_score_below_0.92']}",
        f"- Unsafe final_gate rows: {counters['final_gate_not_import_candidate_high_only']}",
        f"- Missing component rows: {counters['missing_profile_components']}",
        f"- Unparseable wm_avg_score rows: {counters['wm_avg_score_not_parseable']}",
        f"- Unparseable wm_review_count rows: {counters['wm_review_count_not_parseable']}",
        "",
        "## Import Actions",
    ])
    for action in (
        "import_candidate",
        "skip_existing_profile",
        "block_missing_fk",
        "block_low_match_score",
        "block_duplicate",
        "block_missing_profile_components",
        "block_invalid_source_row",
    ):
        report.append(f"- {action}: {action_counts[action]}")
    report.extend([
        "",
        "## Gate",
        f"- Decision: {gate}",
        f"- Safe importable rows: {action_counts['import_candidate']}",
        f"- Import preview: `{os.path.relpath(PREVIEW_CSV, BASE_DIR)}`",
    ])
    with open(DRY_RUN_REPORT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(report) + "\n")

    conflicts = [
        "# Whiskey Mapper Existing Profile Conflict Report",
        "",
        f"Existing `flavor_profiles` conflicts: {action_counts['skip_existing_profile']}",
        f"Duplicate matched_product_id values: {len(duplicate_ids)}",
        "",
        "## Duplicate IDs",
    ]
    if duplicate_ids:
        for duplicate_id in sorted(duplicate_ids):
            duplicate_rows = [row for row in preview_rows if row["whisky_id"] == duplicate_id]
            conflicts.append(f"- {duplicate_id}: {len(duplicate_rows)} rows")
    else:
        conflicts.append("None")
    conflicts.extend(["", "## Existing Profile Rows"])
    existing_rows = [row for row in preview_rows if row["import_action"] == "skip_existing_profile"]
    if existing_rows:
        for row in existing_rows[:100]:
            conflicts.append(f"- {row['whisky_id']}: {row['wm_name']} -> {row['whisky_name']}")
    else:
        conflicts.append("None")
    with open(CONFLICT_REPORT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(conflicts) + "\n")

    gate_lines = [
        "11D-WM-VALIDATE Whiskey Mapper Import Go/No-Go Gate",
        "====================================================",
        f"Decision: {gate}",
        f"CSV rows: {len(input_rows)}",
        f"Safe importable rows: {action_counts['import_candidate']}",
        f"FK missing: {fk_missing}",
        f"Import-candidate low score rows: {low_score_in_import}",
        f"Duplicate matched_product_id values: {len(duplicate_ids)}",
        f"Existing profile skips: {action_counts['skip_existing_profile']}",
    ]
    with open(GATE_REPORT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(gate_lines) + "\n")

    return gate, action_counts


def main():
    try:
        input_rows = read_csv(INPUT_CSV)
    except Exception as exc:
        os.makedirs(REPORT_DIR, exist_ok=True)
        message = (
            "11D-WM-VALIDATE Whiskey Mapper Import Go/No-Go Gate\n"
            "====================================================\n"
            "Decision: NO-GO\n"
            f"CSV read error: {exc}\n"
        )
        with open(GATE_REPORT, "w", encoding="utf-8") as handle:
            handle.write(message)
        raise

    whiskies, existing_profiles, table_counts = load_db_sets()
    duplicate_ids, duplicate_winners = choose_duplicate_winners(input_rows)
    preview_rows, counters = build_preview(input_rows, whiskies, existing_profiles, duplicate_ids, duplicate_winners)
    write_preview(preview_rows)
    gate, action_counts = write_reports(input_rows, preview_rows, counters, table_counts, duplicate_ids)

    print(f"CSV rows: {len(input_rows)}")
    print(f"Preview rows: {len(preview_rows)}")
    print(f"import_candidate: {action_counts['import_candidate']}")
    print(f"Decision: {gate}")
    print(PREVIEW_CSV)


if __name__ == "__main__":
    main()
