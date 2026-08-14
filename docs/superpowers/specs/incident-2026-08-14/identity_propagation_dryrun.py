# AL-MD-01 Phase 1 DRY-RUN — distillery->whisky country/region propagation.
# READ-ONLY: mode=ro, no mutation. Produces the candidate report for APPLY GO.
import sqlite3, hashlib, json, os, datetime

PROD = r"C:\Users\eltun\Documents\malt radar CLEAN\output\import\production.db"
OUT_DIR = r"C:\Users\eltun\Documents\malt radar CLEAN\output\staging\canonical_product_audit_2026-08-13"
sha_before = hashlib.sha256(open(PROD, "rb").read()).hexdigest()
c = sqlite3.connect(f"file:{PROD}?mode=ro", uri=True)
c.row_factory = sqlite3.Row
W = lambda q, *a: c.execute(q, a).fetchall()
one = lambda q, *a: c.execute(q, a).fetchone()[0]
ACT = "(w.superseded_by IS NULL OR w.superseded_by='')"

def candidates(col):
    """Active whisky + distillery_id + missing col + master has col -> (whisky_id, name, dist, old, new)."""
    rows = W(
        f"SELECT w.whisky_id, w.name, w.distillery_id, w.{col} AS old, d.{col} AS new "
        f"FROM whiskies w JOIN distilleries d ON w.distillery_id = d.distillery_id "
        f"WHERE {ACT} AND (w.{col} IS NULL OR w.{col}='') "
        f"AND d.{col} IS NOT NULL AND d.{col}!='' "
        f"ORDER BY w.whisky_id")
    return [dict(r) for r in rows]

def conflicts(col):
    """Active whisky with a PRESENT col that differs from master (no-clobber: excluded, triage)."""
    rows = W(
        f"SELECT w.whisky_id, w.name, w.{col} AS whisky_val, d.{col} AS master_val "
        f"FROM whiskies w JOIN distilleries d ON w.distillery_id = d.distillery_id "
        f"WHERE {ACT} AND w.{col} IS NOT NULL AND w.{col}!='' "
        f"AND d.{col} IS NOT NULL AND d.{col}!='' AND w.{col} != d.{col} "
        f"ORDER BY w.whisky_id LIMIT 100")
    return [dict(r) for r in rows]

report: dict = {"generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}
for col in ["country", "region"]:
    cands = candidates(col)
    report[f"{col}_candidates"] = len(cands)
    report[f"{col}_sample"] = cands[:5]
    # distinct new values sanity
    vals = {}
    for r in cands:
        vals[r["new"]] = vals.get(r["new"], 0) + 1
    report[f"{col}_new_value_counts_top"] = sorted(vals.items(), key=lambda x: -x[1])[:5]
    conf = conflicts(col)
    report[f"{col}_conflicts"] = len(conf)
    report[f"{col}_conflict_sample"] = conf[:5]

# guarded no-clobber re-check: none of the candidates' rows get OVERWRITTEN (only null/empty targets)
report["fk_check_rows"] = len(W("PRAGMA foreign_key_check"))
report["integrity_check"] = one("PRAGMA integrity_check")
report["distillery_orphans"] = one(
    "SELECT COUNT(*) FROM whiskies WHERE distillery_id IS NOT NULL AND distillery_id!='' "
    "AND distillery_id NOT IN (SELECT distillery_id FROM distilleries)")

sha_after = hashlib.sha256(open(PROD, "rb").read()).hexdigest()
report["sha_before"] = sha_before
report["sha_unchanged"] = sha_before == sha_after
report["sha_prefix"] = sha_before[:16]

os.makedirs(OUT_DIR, exist_ok=True)
with open(os.path.join(OUT_DIR, "PHASE1_DRYRUN.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2, default=str)

print(json.dumps({k: v for k, v in report.items() if k != "generated_at"}, ensure_ascii=False, indent=2, default=str)[:4000])
print("\nSHA unchanged:", report["sha_unchanged"], "| integrity:", report["integrity_check"], "| FK rows:", report["fk_check_rows"])
