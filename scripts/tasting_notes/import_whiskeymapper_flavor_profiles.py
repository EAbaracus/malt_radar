import argparse
import csv
import json
import os
import shutil
import sqlite3
from collections import Counter
from decimal import Decimal, InvalidOperation


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PREVIEW_CSV = os.path.join(BASE_DIR, "data", "output", "whiskeymapper_import_preview_remapped.csv")
DB_PATH = os.path.join(BASE_DIR, "output", "import", "production.db")
BACKUP_PATH = os.path.join(BASE_DIR, "output", "import", "production_before_whiskeymapper_import.db")
REPORT_DIR = os.path.join(BASE_DIR, "output", "reports")
DRY_RUN_REPORT = os.path.join(REPORT_DIR, "200_whiskeymapper_import_dry_run_report.md")
APPLY_REPORT = os.path.join(REPORT_DIR, "201_whiskeymapper_import_apply_report.md")
GATE_REPORT = os.path.join(REPORT_DIR, "202_whiskeymapper_import_go_no_go_gate.txt")

NOTES_FOR_REVIEW = (
    "Imported from Whiskey Mapper high-confidence remapped candidate. "
    "External quantitative profile; not editorial tasting note."
)


def read_preview():
    with open(PREVIEW_CSV, "r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_decimal(value):
    value = "" if value is None else str(value).strip()
    if value == "":
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def parse_float(value):
    parsed = parse_decimal(value)
    return float(parsed) if parsed is not None else None


def load_db_state(conn):
    cur = conn.cursor()
    cur.execute("SELECT whisky_id FROM whiskies")
    whisky_ids = {row[0] for row in cur.fetchall()}
    cur.execute("SELECT whisky_id FROM flavor_profiles")
    profile_ids = [row[0] for row in cur.fetchall()]
    cur.execute("SELECT COUNT(*) FROM flavor_profiles")
    flavor_profile_count = cur.fetchone()[0]
    return whisky_ids, set(profile_ids), profile_ids, flavor_profile_count


def duplicate_profile_ids(conn):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT whisky_id, COUNT(*)
        FROM flavor_profiles
        GROUP BY whisky_id
        HAVING COUNT(*) > 1
        """
    )
    return {row[0]: row[1] for row in cur.fetchall()}


def fk_violations(conn):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT fp.whisky_id
        FROM flavor_profiles fp
        LEFT JOIN whiskies w ON w.whisky_id = fp.whisky_id
        WHERE w.whisky_id IS NULL
        """
    )
    return [row[0] for row in cur.fetchall()]


def component_json(row, source_field):
    raw = row.get(source_field) or ""
    try:
        payload = json.loads(raw)
        if isinstance(payload, dict) and payload:
            return json.dumps(payload, ensure_ascii=False, sort_keys=True)
    except json.JSONDecodeError:
        pass
    payload = {
        "component_1": row.get("wm_component_1", ""),
        "component_2": row.get("wm_component_2", ""),
        "component_3": row.get("wm_component_3", ""),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def flavor_tags(row):
    tags = []
    for key in ("wm_component_1", "wm_component_2", "wm_component_3"):
        if (row.get(key) or "").strip():
            tags.append(key.replace("wm_", ""))
    return json.dumps(tags or ["component_1", "component_2", "component_3"], ensure_ascii=False)


def match_score_value(row):
    remap = parse_decimal(row.get("remap_score"))
    original = parse_decimal(row.get("match_score"))
    value = remap if remap is not None else original
    if value is None:
        return None
    # Existing table stores this as INTEGER; keep the established 0-100 scale.
    return int(round(float(value) * 100))


def candidate_rows(rows):
    return [row for row in rows if (row.get("import_action") or "").strip() == "import_candidate"]


def preflight(rows, conn):
    candidates = candidate_rows(rows)
    whisky_ids, existing_profile_ids, _, before_count = load_db_state(conn)
    candidate_ids = [row.get("whisky_id", "").strip() for row in candidates]
    duplicate_targets = {wid: count for wid, count in Counter(candidate_ids).items() if wid and count > 1}
    fk_missing = [wid for wid in candidate_ids if wid not in whisky_ids]
    existing_conflicts = [wid for wid in candidate_ids if wid in existing_profile_ids]
    missing_components = [
        row.get("whisky_id", "")
        for row in candidates
        if not all((row.get(field) or "").strip() for field in ("wm_component_1", "wm_component_2", "wm_component_3"))
    ]
    backup_parent_ready = os.path.isdir(os.path.dirname(BACKUP_PATH))
    return {
        "total_rows": len(rows),
        "import_candidates": len(candidates),
        "before_count": before_count,
        "duplicate_targets": duplicate_targets,
        "fk_missing": fk_missing,
        "existing_conflicts": existing_conflicts,
        "missing_components": missing_components,
        "backup_parent_ready": backup_parent_ready,
    }


def write_gate(mode, decision, lines):
    gate_lines = [
        "11E-WM-IMPORT Whiskey Mapper Flavor Profile Import Gate",
        "=======================================================",
        f"Mode: {mode}",
        f"Decision: {decision}",
    ]
    gate_lines.extend(lines)
    with open(GATE_REPORT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(gate_lines) + "\n")


def write_dry_run_report(rows, state):
    action_counts = Counter(row.get("import_action", "") for row in rows)
    dry_go = (
        state["import_candidates"] >= 250
        and not state["fk_missing"]
        and not state["duplicate_targets"]
        and state["backup_parent_ready"]
    )
    decision = "GO" if dry_go else "NO-GO"
    lines = [
        "# Whiskey Mapper Import Dry-Run Report",
        "",
        "## Safety",
        "- DB write: NO",
        "- Run with `--apply` to insert rows.",
        "",
        "## Inputs",
        f"- Preview CSV: `{os.path.relpath(PREVIEW_CSV, BASE_DIR)}`",
        f"- Production DB: `{os.path.relpath(DB_PATH, BASE_DIR)}`",
        f"- Backup path: `{os.path.relpath(BACKUP_PATH, BASE_DIR)}`",
        "",
        "## Counts",
        f"- Preview rows: {state['total_rows']}",
        f"- import_candidate rows: {state['import_candidates']}",
        f"- flavor_profiles before count: {state['before_count']}",
        f"- skip_existing_profile rows: {action_counts['skip_existing_profile']}",
        f"- blocked rows: {sum(count for action, count in action_counts.items() if action.startswith('block_'))}",
        "",
        "## Preflight Checks",
        f"- FK missing among import candidates: {len(state['fk_missing'])}",
        f"- Duplicate target whisky_id among import candidates: {len(state['duplicate_targets'])}",
        f"- Existing flavor_profiles conflicts among import candidates: {len(state['existing_conflicts'])}",
        f"- Missing component rows among import candidates: {len(state['missing_components'])}",
        f"- Backup parent directory ready: {state['backup_parent_ready']}",
        "",
        "## Gate",
        f"- Decision: {decision}",
    ]
    with open(DRY_RUN_REPORT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    write_gate(
        "dry-run",
        decision,
        [
            f"Import candidates: {state['import_candidates']}",
            f"FK missing: {len(state['fk_missing'])}",
            f"Duplicate targets: {len(state['duplicate_targets'])}",
            f"Backup parent ready: {state['backup_parent_ready']}",
        ],
    )
    return decision


def backup_database():
    os.makedirs(os.path.dirname(BACKUP_PATH), exist_ok=True)
    shutil.copy2(DB_PATH, BACKUP_PATH)
    return BACKUP_PATH


def insert_row(cur, row):
    cur.execute(
        """
        INSERT INTO flavor_profiles (
            whisky_id,
            whisky_name,
            production_bottle_name,
            match_score,
            match_method,
            flavor_vector,
            flavor_profile,
            flavor_tags,
            flavor_source,
            flavor_data_confidence,
            production_price,
            production_rating,
            production_region,
            notes_for_review
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row.get("whisky_id", "").strip(),
            row.get("whisky_name", "").strip(),
            row.get("wm_name", "").strip(),
            match_score_value(row),
            "whiskeymapper_remap",
            component_json(row, "source_profile"),
            component_json(row, "converted_flavor_profile"),
            flavor_tags(row),
            "whiskeymapper",
            "medium",
            None,
            parse_float(row.get("wm_avg_score")),
            None,
            NOTES_FOR_REVIEW,
        ),
    )


def apply_import(rows):
    candidates = candidate_rows(rows)
    backup_path = backup_database()
    conn = sqlite3.connect(DB_PATH)
    inserted = 0
    skipped_existing_at_apply = 0
    rollback_required = False
    error = ""

    try:
        whisky_ids, existing_profile_ids, _, before_count = load_db_state(conn)
        conn.execute("BEGIN")
        cur = conn.cursor()
        for row in candidates:
            whisky_id = row.get("whisky_id", "").strip()
            if whisky_id in existing_profile_ids:
                skipped_existing_at_apply += 1
                continue
            if whisky_id not in whisky_ids:
                raise RuntimeError(f"FK missing for whisky_id={whisky_id}")
            insert_row(cur, row)
            existing_profile_ids.add(whisky_id)
            inserted += 1

        after_count_in_tx = cur.execute("SELECT COUNT(*) FROM flavor_profiles").fetchone()[0]
        if after_count_in_tx != before_count + inserted:
            raise RuntimeError(
                f"Count mismatch before commit: before={before_count} inserted={inserted} after={after_count_in_tx}"
            )
        if fk_violations(conn):
            raise RuntimeError("FK validation failed after insert")
        duplicates = duplicate_profile_ids(conn)
        if duplicates:
            raise RuntimeError(f"Duplicate flavor_profiles whisky_id detected: {duplicates}")
        if inserted == 0:
            raise RuntimeError("insert_count is 0")

        conn.commit()
    except Exception as exc:
        rollback_required = True
        error = str(exc)
        conn.rollback()
    finally:
        conn.close()

    verify_conn = sqlite3.connect(DB_PATH)
    try:
        _, _, _, final_count = load_db_state(verify_conn)
        final_fk_violations = fk_violations(verify_conn)
        final_duplicates = duplicate_profile_ids(verify_conn)
    finally:
        verify_conn.close()

    return {
        "backup_path": backup_path,
        "inserted": inserted,
        "skipped_existing_at_apply": skipped_existing_at_apply,
        "rollback_required": rollback_required,
        "error": error,
        "final_count": final_count,
        "final_fk_violations": final_fk_violations,
        "final_duplicates": final_duplicates,
    }


def write_apply_report(rows, pre_state, apply_state):
    expected_count = pre_state["before_count"] + apply_state["inserted"]
    apply_go = (
        apply_state["inserted"] >= 250
        and apply_state["final_count"] == expected_count
        and not apply_state["final_fk_violations"]
        and not apply_state["final_duplicates"]
        and not apply_state["rollback_required"]
    )
    decision = "GO" if apply_go else "NO-GO"
    lines = [
        "# Whiskey Mapper Import Apply Report",
        "",
        "## Safety",
        f"- Backup created: `{os.path.relpath(apply_state['backup_path'], BASE_DIR)}`",
        "- Transaction used: YES",
        f"- Rollback required: {apply_state['rollback_required']}",
        "",
        "## Counts",
        f"- Preview rows: {len(rows)}",
        f"- import_candidate rows before apply: {pre_state['import_candidates']}",
        f"- flavor_profiles before count: {pre_state['before_count']}",
        f"- insert_count: {apply_state['inserted']}",
        f"- skip_existing_at_apply: {apply_state['skipped_existing_at_apply']}",
        f"- flavor_profiles final count: {apply_state['final_count']}",
        f"- expected final count: {expected_count}",
        "",
        "## Post-Import Checks",
        f"- FK violations: {len(apply_state['final_fk_violations'])}",
        f"- Duplicate flavor_profiles whisky_id values: {len(apply_state['final_duplicates'])}",
        f"- Error: {apply_state['error'] or 'None'}",
        "",
        "## Gate",
        f"- Decision: {decision}",
    ]
    with open(APPLY_REPORT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    write_gate(
        "apply",
        decision,
        [
            f"Insert count: {apply_state['inserted']}",
            f"Before count: {pre_state['before_count']}",
            f"Final count: {apply_state['final_count']}",
            f"Expected final count: {expected_count}",
            f"FK violations: {len(apply_state['final_fk_violations'])}",
            f"Duplicate whisky_id values: {len(apply_state['final_duplicates'])}",
            f"Rollback required: {apply_state['rollback_required']}",
            f"Backup: {os.path.relpath(apply_state['backup_path'], BASE_DIR)}",
        ],
    )
    return decision


def main():
    parser = argparse.ArgumentParser(description="Dry-run or apply Whiskey Mapper flavor profile imports.")
    parser.add_argument("--dry-run", action="store_true", help="Validate only; this is the default.")
    parser.add_argument("--apply", action="store_true", help="Create a backup and insert import_candidate rows.")
    args = parser.parse_args()

    if args.dry_run and args.apply:
        raise SystemExit("Use either --dry-run or --apply, not both.")

    rows = read_preview()
    conn = sqlite3.connect(DB_PATH)
    try:
        state = preflight(rows, conn)
    finally:
        conn.close()

    if not args.apply:
        decision = write_dry_run_report(rows, state)
        print(f"Mode: dry-run")
        print(f"Decision: {decision}")
        print(f"import_candidate: {state['import_candidates']}")
        print(f"FK missing: {len(state['fk_missing'])}")
        print(f"Duplicate targets: {len(state['duplicate_targets'])}")
        print(DRY_RUN_REPORT)
        return

    if not state["backup_parent_ready"]:
        write_gate("apply", "NO-GO", ["Backup parent directory is not ready."])
        raise SystemExit("Backup parent directory is not ready.")

    apply_state = apply_import(rows)
    decision = write_apply_report(rows, state, apply_state)
    print("Mode: apply")
    print(f"Decision: {decision}")
    print(f"insert_count: {apply_state['inserted']}")
    print(f"final_count: {apply_state['final_count']}")
    print(APPLY_REPORT)


if __name__ == "__main__":
    main()
