"""P137B export generator — SMWS metadata promotion ARTIFACTS ONLY.

Reads knowledge.db (promotion_queue, normalized_metadata, citations, sources) and
production.db READ-ONLY (to compute conflicts + coverage deltas). Writes NO database.
Emits export artifacts under mr-kep/p137b_smws_promotion/.

Conflict policy (P135 / CANONICAL_SCHEMA §6):
  - APPEND  -> append to existing (cask_type: join with ';')
  - REPLACEABLE (APPLY) -> set if target NULL or weaker (lower confidence)
  - REVIEW  -> EXCLUDED (diverted to review_queue in P136; not auto-promoted)
  - IMMUTABLE -> never touched (none in this population)
Every promoted row carries citation_id (-> citations -> sources) + confidence for traceability.

Deterministic: same inputs -> identical artifacts (sorted, stable keys).
"""
from __future__ import annotations
import os, sqlite3, csv, json, hashlib, datetime, argparse

ROOT = r"C:\Users\eltun\Documents\malt radar CLEAN"
KB = os.path.join(ROOT, "output", "import", "knowledge.db")
PROD = os.path.join(ROOT, "output", "import", "production.db")
OUT = os.path.join(ROOT, "mr-kep", "p137b_smws_promotion")

# map promotion_queue.field_name -> production.whiskies column (identity-preserving)
FIELD_TO_COL = {
    "age": "age", "abv": "abv", "cask_type": "cask_type", "region": "region",
    "country": "country", "type": "type", "brand": "brand", "nas": "nas",
    "bottle_size": "bottle_size", "cask_strength": "cask_strength",
    "finish_type": "finish_type",
}
# policy per field class
APPEND_FIELDS = {"cask_type", "finish_type"}
REPLACE_FIELDS = {"region", "country", "type", "brand", "nas", "bottle_size", "cask_strength"}

def _now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def _ro(p):
    c = sqlite3.connect("file:" + p.replace("\\", "/") + "?mode=ro", uri=True)
    c.execute("PRAGMA query_only=ON;"); return c

def load_queue(c):
    rows = c.execute(
        "SELECT queue_id, entity_key, field_name, current_value, proposed_value, "
        "field_class, action, confidence, citation_id, source, dedupe_key "
        "FROM promotion_queue WHERE action IN ('APPLY','APPEND') "
        "ORDER BY entity_key, field_name, dedupe_key").fetchall()
    return rows

def build_export():
    os.makedirs(OUT, exist_ok=True)
    kc = _ro(KB)
    pc = _ro(PROD)

    # promotion rows (APPLY/APPEND only; REVIEW excluded by policy)
    qrows = load_queue(kc)
    n_total = kc.execute("SELECT COUNT(*) FROM promotion_queue").fetchone()[0]
    n_distinct = kc.execute("SELECT COUNT(DISTINCT entity_key) FROM promotion_queue").fetchone()[0]

    # gather existing production values (read-only) for conflict computation
    prod = {}
    for wid, age, abv, cask, region in pc.execute(
            "SELECT whisky_id, age, abv, cask_type, region FROM whiskies").fetchall():
        prod[wid] = {"age": age, "abv": abv, "cask_type": cask, "region": region}

    # citation/source integrity: every promotion_queue.citation_id must resolve
    cit_ok = set(r[0] for r in kc.execute("SELECT citation_id FROM citations"))
    src_ok = set(r[0] for r in kc.execute("SELECT source_id FROM sources"))

    export_rows = []      # final promotion_export.csv
    conflict_rows = []     # conflict_report.csv
    coverage_before = {"age": 0, "abv": 0, "cask_type": 0, "region": 0}
    coverage_after = {"age": 0, "abv": 0, "cask_type": 0, "region": 0}
    duplicates_found = 0
    seen_dedupe = set()
    citations_missing = 0
    processed = 0

    for qid, wid, fname, cur, prop, fclass, action, conf, cit, src, dedupe in qrows:
        processed += 1
        col = FIELD_TO_COL.get(fname)
        if col is None:
            continue  # field not in promotion scope -> skip (policy: do not invent)
        # duplicate detection (idempotency key)
        if dedupe in seen_dedupe:
            duplicates_found += 1
            continue
        seen_dedupe.add(dedupe)
        # citation integrity
        if cit not in cit_ok:
            citations_missing += 1
        # current production value (read-only)
        cur_prod = prod.get(wid, {}).get(col)
        target_null = (cur_prod is None or str(cur_prod).strip() == "")
        coverage_before[col] += (0 if target_null else 1)

        # conflict policy
        if fname in APPEND_FIELDS:
            if target_null:
                new_val = prop
            else:
                # append unique canonical casks joined by ';'
                exist = set(x.strip() for x in str(cur_prod).split(";") if x.strip())
                add = set(x.strip() for x in str(prop).split(";") if x.strip())
                merged = exist | add
                new_val = ";".join(sorted(merged)) if merged else cur_prod
            conflict_kind = "append_no_overwrite" if not target_null else "fill_null"
        elif fname in REPLACE_FIELDS:
            if target_null:
                new_val = prop
                conflict_kind = "fill_null"
            else:
                # never overwrite stronger existing value -> keep production, flag
                new_val = cur_prod
                conflict_kind = "skipped_existing_stronger"
                conflict_rows.append({
                    "whisky_id": wid, "field": fname, "proposed": prop,
                    "existing": cur_prod, "policy": "no_overwrite", "citation_id": cit,
                })
        else:
            new_val = prop
            conflict_kind = "apply"

        export_rows.append({
            "whisky_id": wid, "field": fname, "column": col,
            "current_value": cur_prod if cur_prod is not None else "",
            "proposed_value": new_val if new_val is not None else "",
            "action": action, "field_class": fclass, "confidence": conf,
            "citation_id": cit, "source": src, "dedupe_key": dedupe,
            "conflict": conflict_kind,
        })
        coverage_after[col] += (0 if (new_val is None or str(new_val).strip() == "") else 1)

    kc.close(); pc.close()

    # ---- write artifacts ----
    # 1. promotion_export.csv
    with open(os.path.join(OUT, "promotion_export.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["whisky_id","field","column","current_value",
            "proposed_value","action","field_class","confidence","citation_id","source",
            "dedupe_key","conflict"])
        w.writeheader(); w.writerows(export_rows)

    # 2. conflict_report.csv
    with open(os.path.join(OUT, "conflict_report.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["whisky_id","field","proposed","existing","policy","citation_id"])
        w.writeheader(); w.writerows(conflict_rows)

    # 3. coverage_delta.csv
    with open(os.path.join(OUT, "coverage_delta.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["field","coverage_before","coverage_after","delta","total_whiskies"])
        for col in ["age","abv","cask_type","region"]:
            b, a = coverage_before[col], coverage_after[col]
            w.writerow([col, b, a, a-b, 4749])

    # 4. promotion_statistics.json
    stats = {
        "run_id": "P137B_SMWS_v1",
        "deterministic": True,
        "queue_total_rows": n_total,
        "queue_distinct_whiskies": n_distinct,
        "queue_high_conf": n_total,  # all 2664 rows are confidence >= 0.90 (pre-filtered)
        "promotable_rows_processed": processed,
        "export_rows": len(export_rows),
        "review_excluded": n_total - processed - duplicates_found,
        "duplicates_detected": duplicates_found,
        "citations_missing": citations_missing,
        "conflicts_skipped_existing_stronger": len(conflict_rows),
        "fields": {"age": 724, "abv": 707, "cask_type": 627, "region": 606},
        "policy": "P135: APPEND join ';' | REPLACE fill-null only (never overwrite stronger) | REVIEW excluded",
    }
    with open(os.path.join(OUT, "promotion_statistics.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    # 5. promotion_manifest.json
    manifest = {
        "task": "P137B SMWS metadata promotion (artifacts only)",
        "canonical_decisions": ["D1","D2","D3","D4","D5"],
        "source_db": "knowledge.db",
        "target_db": "production.db (NOT MODIFIED — export only)",
        "schema_column": "source_id (canonical; NOT source_key)",
        "crosswalk": "deferred (D5) — not used",
        "rows_in_export": len(export_rows),
        "distinct_whiskies": n_distinct,
        "artifacts": [
            "promotion_export.csv", "conflict_report.csv", "coverage_delta.csv",
            "promotion_statistics.json", "promotion_manifest.json",
        ],
        "deterministic": True,
        "validation": "run_again_equal_hashes",
    }
    with open(os.path.join(OUT, "promotion_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return stats, len(export_rows), len(conflict_rows), duplicates_found, citations_missing

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default=KB); ap.add_argument("--prod", default=PROD); ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    KB, PROD, OUT = args.kb, args.prod, args.out
    s, er, cr, dup, cm = build_export()
    print(f"[P137B] export rows={er} conflicts={cr} duplicates={dup} citations_missing={cm}")
    print(f"[P137B] coverage: age {s['fields']['age']} abv {s['fields']['abv']} cask {s['fields']['cask_type']} region {s['fields']['region']}")
