import csv
import hashlib
import sqlite3
from collections import Counter
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DECISION_CSV = Path(r"C:\Users\eltun\Downloads\scotchgit_qa_pack_v8_DECISION_GATE_READY.csv")
PREVIEW_CSV = BASE_DIR / "data" / "output" / "scotchgit_flavor_signal_preview.csv"
WHISKEYMAPPER_REMAP_CSV = BASE_DIR / "data" / "output" / "whiskeymapper_import_preview_remapped.csv"
WHISKEYMAPPER_HIGH_CSV = BASE_DIR / "data" / "output" / "whiskeymapper_final_import_candidates_high_only.csv"
DB_PATH = BASE_DIR / "output" / "import" / "production.db"

OUTPUT_CSV = BASE_DIR / "data" / "output" / "scotchgit_flavor_preview_import.csv"
HOLD_REPORT = BASE_DIR / "output" / "reports" / "204_scotchgit_preview_hold_report.md"
CONFLICT_REPORT = BASE_DIR / "output" / "reports" / "205_scotchgit_vs_whiskeymapper_conflict_report.md"
GATE_TXT = BASE_DIR / "output" / "reports" / "206_scotchgit_preview_go_no_go_gate.txt"

OUTPUT_FIELDS = [
    "matched_product_id",
    "matched_master_whisky_id",
    "product_name",
    "smoky",
    "sweet",
    "fruity",
    "spicy",
    "woody",
    "maritime",
    "sherry",
    "signal_strength",
    "signal_basis",
    "confidence_note",
    "confidence_warning",
    "source_rows",
    "high_rows",
    "medium_rows",
    "source_url_count",
    "review_count_total",
    "web_review_decision",
    "web_review_status",
    "web_review_confidence",
    "web_review_rationale",
    "web_review_sources",
    "scotchgit_priority",
    "has_existing_production_profile",
    "has_whiskeymapper_candidate",
    "conflict_status",
    "production_import_status",
]


def clean(value):
    return str(value or "").strip()


def sha256_file(path):
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def production_profile_ids():
    if not DB_PATH.exists():
        return set()
    conn = sqlite3.connect(DB_PATH.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        return {clean(row[0]) for row in conn.execute("SELECT whisky_id FROM flavor_profiles") if clean(row[0])}
    finally:
        conn.close()


def whiskeymapper_candidate_ids():
    ids = set()
    for row in read_csv(WHISKEYMAPPER_REMAP_CSV):
        if clean(row.get("import_action")) in {"import_candidate", "preview_candidate", "IMPORT_CANDIDATE_HIGH_ONLY"}:
            ids.add(clean(row.get("whisky_id")))
    for row in read_csv(WHISKEYMAPPER_HIGH_CSV):
        # This older file may still contain WDB ids; include it for audit completeness.
        ids.add(clean(row.get("matched_product_id")))
    return {value for value in ids if value}


def keyed_preview_rows():
    return {clean(row.get("matched_master_whisky_id")): row for row in read_csv(PREVIEW_CSV)}


def main():
    db_hash_before = sha256_file(DB_PATH)
    decisions = read_csv(DECISION_CSV)
    accepted = [row for row in decisions if clean(row.get("web_review_decision")) == "accept_preview"]
    preview_by_id = keyed_preview_rows()
    production_ids = production_profile_ids()
    wm_ids = whiskeymapper_candidate_ids()

    output_rows = []
    missing_preview = []
    for row in accepted:
        whisky_id = clean(row.get("matched_master_whisky_id"))
        preview = preview_by_id.get(whisky_id)
        if not preview:
            missing_preview.append(whisky_id)
            preview = {}

        has_production = whisky_id in production_ids
        has_wm = whisky_id in wm_ids
        conflicts = []
        if has_production:
            conflicts.append("existing_production_profile")
        if has_wm:
            conflicts.append("whiskeymapper_candidate")
        conflict_status = "|".join(conflicts) if conflicts else "no_conflict"

        out = {
            "matched_product_id": whisky_id,
            "matched_master_whisky_id": whisky_id,
            "product_name": clean(row.get("product_name") or preview.get("product_name")),
            "web_review_decision": clean(row.get("web_review_decision")),
            "web_review_status": clean(row.get("web_review_status")),
            "web_review_confidence": clean(row.get("web_review_confidence")),
            "web_review_rationale": clean(row.get("web_review_rationale")),
            "web_review_sources": clean(row.get("web_review_sources")),
            "scotchgit_priority": "lower_than_existing_or_whiskeymapper" if conflicts else "preview_whitelist",
            "has_existing_production_profile": 1 if has_production else 0,
            "has_whiskeymapper_candidate": 1 if has_wm else 0,
            "conflict_status": conflict_status,
            "production_import_status": "preview_whitelist_only",
        }
        for field in [
            "smoky",
            "sweet",
            "fruity",
            "spicy",
            "woody",
            "maritime",
            "sherry",
            "signal_strength",
            "signal_basis",
            "confidence_note",
            "confidence_warning",
            "source_rows",
            "high_rows",
            "medium_rows",
            "source_url_count",
            "review_count_total",
        ]:
            out[field] = clean(preview.get(field) or row.get(field))
        output_rows.append(out)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(output_rows)

    db_hash_after = sha256_file(DB_PATH)
    db_changed = bool(db_hash_before and db_hash_after and db_hash_before != db_hash_after)
    conflict_counts = Counter(row["conflict_status"] for row in output_rows)
    priority_counts = Counter(row["scotchgit_priority"] for row in output_rows)

    HOLD_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with HOLD_REPORT.open("w", encoding="utf-8") as fh:
        fh.write("# ScotchGit Preview Hold Report\n\n")
        fh.write("## Decision\n\n")
        fh.write("- Preview whitelist gate: **GO**\n")
        fh.write("- Production import gate: **NO-GO until 11E-WM-IMPORT is closed**\n")
        fh.write(f"- production.db changed: {'YES' if db_changed else 'NO'}\n")
        fh.write("- ScotchGit remains preview/QA only.\n\n")
        fh.write("## Inputs\n\n")
        fh.write(f"- decision CSV: `{DECISION_CSV}`\n")
        fh.write(f"- decision rows: {len(decisions)}\n")
        fh.write(f"- accept_preview rows: {len(accepted)}\n")
        fh.write(f"- flavor preview rows available: {len(preview_by_id)}\n")
        fh.write(f"- missing accepted preview rows: {len(missing_preview)}\n\n")
        fh.write("## Output\n\n")
        fh.write(f"- preview whitelist CSV: `{OUTPUT_CSV.as_posix()}`\n")
        fh.write(f"- preview whitelist rows: {len(output_rows)}\n\n")
        fh.write("## Priority Counts\n\n")
        for key, count in sorted(priority_counts.items()):
            fh.write(f"- {key}: {count}\n")

    with CONFLICT_REPORT.open("w", encoding="utf-8") as fh:
        fh.write("# ScotchGit vs WhiskeyMapper Conflict Report\n\n")
        fh.write("## Summary\n\n")
        fh.write(f"- ScotchGit accepted preview rows: {len(output_rows)}\n")
        fh.write(f"- production flavor profile ids: {len(production_ids)}\n")
        fh.write(f"- WhiskeyMapper candidate ids: {len(wm_ids)}\n")
        fh.write(f"- production.db changed: {'YES' if db_changed else 'NO'}\n\n")
        fh.write("## Conflict Counts\n\n")
        for key, count in sorted(conflict_counts.items()):
            fh.write(f"- {key}: {count}\n")
        fh.write("\n## Conflict Samples\n\n")
        conflict_rows = [row for row in output_rows if row["conflict_status"] != "no_conflict"]
        if conflict_rows:
            for row in conflict_rows[:50]:
                fh.write(
                    f"- {row['matched_product_id']} | {row['product_name']} | "
                    f"{row['conflict_status']} | priority={row['scotchgit_priority']}\n"
                )
        else:
            fh.write("- None\n")

    with GATE_TXT.open("w", encoding="utf-8") as fh:
        fh.write("ScotchGit preview whitelist: GO\n")
        fh.write("ScotchGit production import: NO-GO until 11E-WM-IMPORT is closed\n")
        fh.write(f"accepted_preview_rows={len(output_rows)}\n")
        fh.write(f"production_db_changed={'YES' if db_changed else 'NO'}\n")
        fh.write("\nEstimated API Cost: $0.00\n")
        fh.write("Actual API Cost: $0.00\n")
        fh.write("Local Compute Used: Yes\n")
        fh.write("Fully Local Execution: Yes\n")

    print(f"ScotchGit preview whitelist rows: {len(output_rows)}")
    print("Preview whitelist: GO")
    print("Production import: NO-GO until 11E-WM-IMPORT is closed")
    print(f"Report written: {HOLD_REPORT}")


if __name__ == "__main__":
    main()
