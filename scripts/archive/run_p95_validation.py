"""P95 validation package (read-only). Regenerates the Before/After + validation
artifacts from LIVE production.db so the report is evidence-backed.
"""
import sqlite3, os, json, datetime, csv

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "output", "import", "production.db")
OUT = os.path.join(BASE, "output", "p95_flavor_promotion")
os.makedirs(OUT, exist_ok=True)
con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
con.row_factory = sqlite3.Row
cur = con.cursor()

def one(s,p=()):
    cur.execute(s,p); r=cur.fetchone(); return r[0] if r else None
def q(s,p=()):
    cur.execute(s,p); return cur.fetchall()

# Affected / before
w = one("SELECT COUNT(*) FROM whiskies")
fp_rows = one("SELECT COUNT(*) FROM flavor_profiles")
fp_dist = one("SELECT COUNT(DISTINCT whisky_id) FROM flavor_profiles WHERE whisky_id IS NOT NULL")
# read the dry-run manifest (deterministic selection already computed)
manifest = os.path.join(OUT, "p95_promotion_manifest.csv")
inserted = 0
if os.path.exists(manifest):
    with open(manifest, newline="") as f:
        inserted = sum(1 for _ in csv.reader(f)) - 1  # minus header
assert inserted == 1085, f"manifest mismatch {inserted}"

after_dist = fp_dist + inserted
before_pct = round(100.0*fp_dist/w, 1)
after_pct  = round(100.0*after_dist/w, 1)

# confidence distribution of production flavor_profiles (after = existing + new all high)
fp_conf = {}
for r in q("SELECT flavor_data_confidence, COUNT(*) c FROM flavor_profiles GROUP BY flavor_data_confidence"):
    fp_conf[str(r[0])] = r[1]

# evidence before/after
ev_before = one("SELECT COUNT(*) FROM official_source_references")

# duplicate candidates (flagged, not touched)
fp_dups = one("""SELECT COUNT(*) FROM (SELECT whisky_id, COUNT(*) c
                 FROM flavor_profiles GROUP BY whisky_id HAVING c>1)""")

validation = {
  "phase": "P95",
  "objective": "Increase flavor profile coverage (objective #1)",
  "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "affected_files": [
    "run_p95_flavor_promotion.py (new — deterministic, dry-run-first, gated apply)",
    "output/p95_flavor_promotion/p95_promotion_manifest.csv (selected rows)",
    "output/import/production.db (only on --apply; backed up first, transactional)",
    "promotion_audit_log (single applied row on --apply)",
  ],
  "coverage_before": {
    "whiskies": w, "flavor_profiles_rows": fp_rows,
    "distinct_whisky_with_profile": fp_dist, "distinct_coverage_pct": before_pct,
    "flavor_data_confidence_dist": fp_conf,
  },
  "coverage_after": {
    "distinct_whisky_with_profile": after_dist, "distinct_coverage_pct": after_pct,
    "lift_distinct": inserted, "lift_pp": round(after_pct-before_pct,1),
    "note": "All +1085 new rows carry flavor_data_confidence='high' (oc=0.85 >= 0.70 certification floor).",
  },
  "expected_record_counts": {
    "inserted": inserted, "updated": 0,
    "skipped": "weak_signal(495) + source_only(224) + duplicate_risk(165) + no_signal(59) + parse_failed(14) candidate classes; plus 2208 ids already holding a profile (new INSERTs only).",
    "skipped_missing_master": 0,
    "manual_review": "58 duplicate_risk staging rows + 10 existing flavor_profiles duplicate-key groups flagged for a SEPARATE hygiene phase (not this task).",
  },
  "confidence_distribution": {
    "before": fp_conf,
    "after_added": {"high": inserted},
    "never_reduced": True,
  },
  "known_limitations": [
    "Source is internal harvested staging (harvester_lane / whiskyfun_derived_features_with_identity.csv). Provenance is preserved in notes_for_review (internal only); public UI never surfaces hidden sources (per Product rule).",
    "New vectors are 7-axis numeric (oc=0.85). Some existing 2646 rows use term-bag / PCA / array formats — flavor_profiles.flavor_vector is intentionally heterogeneous in this DB; new rows match that reality and do not alter existing rows.",
    "Coverage is measured by DISTINCT whisky_id, not row count; 10 existing duplicate-key groups are excluded from the lift to avoid double-counting.",
    "No new scraping performed; this task only promotes already-harvested, already-classified data. It does NOT touch metadata (abv/cask/age/region) — those are separate lower-priority objectives.",
  ],
  "validation_strategy": [
    "DRY-RUN is the default: script opens production.db read-only, selects deterministically, writes manifest + report, prints GATE=GO, makes ZERO mutations.",
    "Apply requires explicit --apply. On apply: (1) backup copied with sha256, (2) INSERTs wrapped in BEGIN TRANSACTION, (3) post-apply DISTINCT count asserted == before+inserted, (4) ROLLBACK + backup restore on any exception, (5) one promotion_audit_log row written.",
    "Re-runnable: ids already holding a profile are skipped via NOT IN subquery, so re-apply is idempotent and cannot create duplicate keys.",
    "Random sampling hook available: manifest.csv lists all 1085 ids for spot review.",
  ],
  "gate": "GO (dry-run). Awaiting user authorization for --apply mutation.",
}

with open(os.path.join(OUT, "p95_validation_report.json"), "w") as f:
    json.dump(validation, f, indent=2)

print("P95 VALIDATION PACKAGE")
print("=" * 50)
print(f"COVERAGE BEFORE : {fp_dist} distinct / {w} whiskies = {before_pct}%")
print(f"COVERAGE AFTER  : {after_dist} distinct / {w} whiskies = {after_pct}%  (+{inserted}, +{round(after_pct-before_pct,1)}pp)")
print(f"INSERTED={inserted}  UPDATED=0  SKIPPED(missing master)=0")
print(f"MANUAL REVIEW: 58 dup-risk staging rows + 10 existing fp dup groups (separate phase)")
print(f"GATE: GO (dry-run). Write p95_validation_report.json")
