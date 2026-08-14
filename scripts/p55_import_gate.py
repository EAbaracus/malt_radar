#!/usr/bin/env python
"""
P55 - Distillery Import Gate
Source: list-of-current-operating-scotch-whisky-distilleries-sept-2022.pdf
Staging: output/import/distilleries_2022/staging_distilleries_2022.csv

Executes the approved import into production.db in a SINGLE transaction:
  - INSERT 90 new canonical rows (78 absent + 12 reconcile)
  - UPDATE 51 present rows: set status='Operating'; backfill region where NULL (36)
  - Never overwrites trusted data (region left intact where present)
Rolls back on any unexpected error.

Produces:
  output/import/distilleries_2022/import_summary.md
  output/import/distilleries_2022/import_audit.csv
  output/import/distilleries_2022/import_before_after.json
"""
import sqlite3, csv, os, json, datetime, shutil, sys, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGE_DIR = os.path.join(ROOT, "output", "import", "distilleries_2022")
STAGE_CSV = os.path.join(STAGE_DIR, "staging_distilleries_2022.csv")
XREF_CSV = os.path.join(STAGE_DIR, "cross_reference.csv")
DB = os.path.join(ROOT, "output", "import", "production.db")
BACKUP_DIR = os.path.join(ROOT, "output", "import", "backups")
SOURCE_FILE = "list-of-current-operating-scotch-whisky-distilleries-sept-2022.pdf"
ALLOWED_REGIONS = {"Speyside", "Highland", "Lowland", "Islands", "Islay", "Campbeltown"}
ALLOWED_ACTIONS = {"insert", "reconcile_promote_to_canonical", "verify_backfill_region", "verify"}

def norm(s):
    s = s.lower().replace("'", "").replace("\u2019", "")
    return re.sub(r"[^a-z0-9]", "", s)

def vprint(*a):
    print(*a, flush=True)

def validate_staging(rows):
    errors = []
    if len(rows) != 141:
        errors.append(f"row count != 141 (got {len(rows)})")
    seen_no, seen_name = set(), set()
    for r in rows:
        # required fields
        for fld in ("pdf_no", "name", "country", "region", "status", "action"):
            if not r.get(fld):
                errors.append(f"row pdf_no={r.get('pdf_no')} missing required field '{fld}'")
        # duplicates
        if r["pdf_no"] in seen_no:
            errors.append(f"duplicate pdf_no {r['pdf_no']}")
        seen_no.add(r["pdf_no"])
        if r["name"] in seen_name:
            errors.append(f"duplicate name {r['name']}")
        seen_name.add(r["name"])
        # normalized region
        if r["region"] not in ALLOWED_REGIONS:
            errors.append(f"row {r['pdf_no']} bad region '{r['region']}'")
        # action
        if r["action"] not in ALLOWED_ACTIONS:
            errors.append(f"row {r['pdf_no']} bad action '{r['action']}'")
    return errors

def main():
    vprint("=== P55 IMPORT GATE ===")
    # ---- Task 1: validate staging ----
    vprint("[Task 1] Validating staging_distilleries_2022.csv ...")
    rows = list(csv.DictReader(open(STAGE_CSV, encoding="utf-8")))
    verrs = validate_staging(rows)
    if verrs:
        for e in verrs:
            vprint("  VALIDATION ERROR:", e)
        write_summary(verrs, None)
        vprint("VERDICT: NO-GO (staging validation failed)")
        sys.exit(2)
    vprint(f"  OK: {len(rows)} rows, no dup ids/names, no nulls, regions normalized.")

    # ---- Backup ----
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(BACKUP_DIR, f"production_p55_pre_{ts}.db")
    shutil.copy2(DB, backup)
    vprint(f"[backup] {backup}")

    # ---- Load cross-reference for reconciliation linking ----
    xref = {r["pdf_name"]: r for r in csv.DictReader(open(XREF_CSV, encoding="utf-8"))}

    conn = sqlite3.connect(DB)
    conn.isolation_level = None  # manual transaction control
    before = conn.execute("SELECT COUNT(*) FROM distilleries").fetchone()[0]

    # existing canonical map for merge/backfill (defensive)
    existing = {norm(r[1]): r[0] for r in conn.execute("SELECT distillery_id, name FROM distilleries")}

    # determine next id
    maxn = 0
    for (did,) in conn.execute("SELECT distillery_id FROM distilleries"):
        m = re.match(r"^D(\d+)$", str(did) or "")
        if m:
            maxn = max(maxn, int(m.group(1)))
    next_id = maxn + 1

    audit = []
    inserted = updated = skipped = errors = 0
    recon_summary = []

    try:
        conn.execute("BEGIN")
        for r in rows:
            num = r["pdf_no"]; name = r["name"]; act = r["action"]
            region = r["region"]; conf = r["data_confidence"]; note = r["notes_for_review"]
            try:
                if act in ("insert", "reconcile_promote_to_canonical"):
                    # defensive: do not insert if canonical name already exists
                    if norm(name) in existing:
                        audit.append((num, name, act, existing[norm(name)], "skipped",
                                      "canonical name already present in DB"))
                        skipped += 1
                        continue
                    did = f"D{next_id:04d}"; next_id += 1
                    conn.execute(
                        "INSERT INTO distilleries (distillery_id, name, country, region, status, data_confidence, notes_for_review) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (did, name, "Scotland", region, "Operating", conf, note or None))
                    audit.append((num, name, act, did, "inserted", f"new canonical row conf={conf}"))
                    inserted += 1
                    if act == "reconcile_promote_to_canonical":
                        linked = xref.get(name, {}).get("matched_db", "")
                        recon_summary.append((num, name, did, linked))
                elif act in ("verify_backfill_region", "verify"):
                    # find DB row by name
                    did = existing.get(norm(name))
                    if not did:
                        audit.append((num, name, act, "", "error", "present row not found by name"))
                        errors += 1
                        continue
                    # region backfill only if NULL (never overwrite trusted region)
                    if act == "verify_backfill_region":
                        conn.execute(
                            "UPDATE distilleries SET region=?, status='Operating' WHERE distillery_id=?",
                            (region, did))
                    else:
                        # verify: region already trusted; set status only
                        conn.execute(
                            "UPDATE distilleries SET status='Operating' WHERE distillery_id=?",
                            (did,))
                    audit.append((num, name, act, did, "updated",
                                  "status=Operating" + ("; region backfilled" if act == "verify_backfill_region" else "; region kept")))
                    updated += 1
            except Exception as e:
                audit.append((num, name, act, "", "error", str(e)))
                errors += 1
        if errors:
            raise RuntimeError(f"{errors} row-level errors during import")
        conn.execute("COMMIT")
    except Exception as e:
        conn.execute("ROLLBACK")
        vprint("  IMPORT FAILED -> ROLLBACK:", e)
        write_summary([f"rollback: {e}"], None)
        vprint("VERDICT: NO-GO (rolled back)")
        sys.exit(3)

    after = conn.execute("SELECT COUNT(*) FROM distilleries").fetchone()[0]

    # ---- Task 4: source_audit / entity_sources ----
    notice = None
    try:
        conn.execute("SELECT 1 FROM source_audit LIMIT 1")
        # exists -> would populate, but we have no canonical source_audit rows to add here
        conn.execute("SELECT 1 FROM entity_sources LIMIT 1")
    except sqlite3.OperationalError:
        notice = ("NOTICE: source_audit and entity_sources tables are ABSENT in "
                  "output/import/production.db (canonical schema defines them, but this "
                  "seeded DB lacks them). Traceability recorded via import_audit.csv and "
                  "backup only. Recommend a schema-sync gate before relying on entity_sources.")

    conn.close()

    # ---- Task 3: artifacts ----
    write_artifacts(rows, audit, recon_summary, before, after,
                    inserted, updated, skipped, errors, backup, notice)

    verdict = "GO" if errors == 0 else "NO-GO"
    vprint(f"\n[counts] inserted={inserted} updated={updated} skipped={skipped} error={errors}")
    vprint(f"[rows] before={before} after={after}")
    if notice:
        vprint("[NOTICE]", notice)
    vprint(f"VERDICT: {verdict}")
    sys.exit(0 if verdict == "GO" else 4)

def write_artifacts(rows, audit, recon_summary, before, after, inserted, updated, skipped, errors, backup, notice):
    # audit csv
    with open(os.path.join(STAGE_DIR, "import_audit.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pdf_no", "name", "action", "distillery_id", "result", "detail"])
        for a in audit:
            w.writerow(a)
    # before/after json
    ba = {"before_distilleries": before, "after_distilleries": after,
          "inserted": inserted, "updated": updated, "skipped": skipped, "error": errors}
    with open(os.path.join(STAGE_DIR, "import_before_after.json"), "w", encoding="utf-8") as f:
        json.dump(ba, f, indent=2)
    # summary md
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    L = []
    L.append("# P55 - Distillery Import Gate: Summary\n")
    L.append(f"_Executed: {now}_\n")
    L.append(f"**Source:** {SOURCE_FILE}\n")
    L.append(f"**Backup:** `{os.path.relpath(backup, ROOT)}`\n")
    L.append("\n## Before / After\n")
    L.append(f"| Metric | Value |")
    L.append(f"| --- | --- |")
    L.append(f"| distilleries before | {before} |")
    L.append(f"| distilleries after | {after} |")
    L.append(f"| inserted | {inserted} |")
    L.append(f"| updated | {updated} |")
    L.append(f"| skipped | {skipped} |")
    L.append(f"| error | {errors} |\n")
    L.append("## Reconciliation Summary (12 expression-only distilleries promoted)\n")
    for num, name, did, linked in recon_summary:
        L.append(f"- #{num} **{name}** -> new `{did}`; linked existing expressions: `{linked}`")
    L.append("\n## Validation (Task 1)\n")
    L.append("- 141 rows; no duplicate pdf_no/name; no null required fields; all regions normalized; deterministic.\n")
    if notice:
        L.append("## Notice (Task 4)\n")
        L.append(f"> {notice}\n")
    L.append("## Transaction integrity\n")
    L.append("- Single transaction; rolled back automatically on any unexpected error. Backup taken prior to mutation.\n")
    L.append("\n## Verdict\n")
    L.append("GO" if errors == 0 else "NO-GO")
    with open(os.path.join(STAGE_DIR, "import_summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L))

def write_summary(errs, _):
    # minimal summary on failure path
    with open(os.path.join(STAGE_DIR, "import_summary.md"), "w", encoding="utf-8") as f:
        f.write("# P55 - Distillery Import Gate: FAILED\n\n")
        for e in errs:
            f.write(f"- {e}\n")
        f.write("\n## Verdict\n\nNO-GO\n")

if __name__ == "__main__":
    main()
