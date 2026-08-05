"""QA audit for unified editorial staging DB (read-only).

Checks (mirrors AGENTS.md completion requirements):
  R1  R4 invariant: every flavor_vector axis in [0.0, 1.0]
  R2  no empty/non-R4 vectors (exactly 7 canonical axes)
  R3  no duplicate (source_id, source_url)
  R4  no NULL normalized_name / raw_name
  R5  score_normalized == score_value/scale_max when both present, in (0,1]
  R6  no NULL evidence_id; evidence_id deterministic format EDR-<16 hex>
  R7  authority_tier == T2_expert
  R8  provenance_state == staging_unverified
  R9  metadata_json parses; abv/age sane ranges when present
  R10 published_date ISO or NULL
Prints a summary + violations (capped). Exit 0 if no violations else 1.
"""
import json
import sqlite3
import sys
from pathlib import Path

DB = Path(sys.argv[1] if len(sys.argv) > 1 else "output/staging/unified_staging.db")
CAP = 10  # violation lines printed per rule

conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cur = conn.cursor()
violations = {f"R{i}": [] for i in range(1, 11)}

def add(rule, msg):
    if len(violations[rule]) < CAP:
        violations[rule].append(msg)

# R1/R2: vectors
rows = cur.execute(
    "SELECT evidence_id, source_id, flavor_vector_json FROM staging_editorial_reviews"
).fetchall()
CANON = {"smoky", "peaty", "fruity", "sweet", "spicy", "maritime", "sherry"}
for eid, src, vec_json in rows:
    try:
        vec = json.loads(vec_json)
    except Exception:
        add("R2", f"unparseable vector: {eid} ({src})")
        continue
    keys = set(vec.keys())
    if keys != CANON:
        add("R2", f"axis mismatch {sorted(keys)}: {eid} ({src})")
        continue
    for k, v in vec.items():
        if not isinstance(v, (int, float)) or not (0.0 <= v <= 1.0):
            add("R1", f"out-of-range {k}={v!r}: {eid} ({src})")

# R3: dupes
for src, url, cnt in cur.execute(
    "SELECT source_id, source_url, COUNT(*) c FROM staging_editorial_reviews "
    "GROUP BY source_id, source_url HAVING c > 1"
):
    add("R3", f"{src} | {url} | x{cnt}")

# R4
for src, cnt in cur.execute(
    "SELECT source_id, COUNT(*) FROM staging_editorial_reviews "
    "WHERE raw_name IS NULL OR normalized_name IS NULL GROUP BY source_id"
):
    add("R4", f"{src}: {cnt} null raw/normalized")

# R5: score consistency
for eid, sv, sm, sn in cur.execute(
    "SELECT evidence_id, score_value, score_scale_max, score_normalized "
    "FROM staging_editorial_reviews WHERE score_value IS NOT NULL"
):
    if not sm or not (0 < sn <= 1.0):
        add("R5", f"bad norm: {eid} sv={sv} sm={sm} sn={sn}")
        continue
    if abs(sn - sv / sm) > 1e-9:
        add("R5", f"norm mismatch: {eid} sv={sv} sm={sm} sn={sn}")

# R6
for eid in cur.execute(
    "SELECT evidence_id FROM staging_editorial_reviews "
    "WHERE evidence_id IS NULL OR evidence_id NOT LIKE 'EDR-%'"
):
    add("R6", f"bad evidence_id: {eid[0]!r}")

# R7/R8
for r7 in cur.execute(
    "SELECT source_id, COUNT(*) FROM staging_editorial_reviews "
    "WHERE authority_tier != 'T2_expert' GROUP BY source_id"
):
    add("R7", f"{r7[0]}: {r7[1]}")
for r8 in cur.execute(
    "SELECT source_id, COUNT(*) FROM staging_editorial_reviews "
    "WHERE provenance_state != 'staging_unverified' GROUP BY source_id"
):
    add("R8", f"{r8[0]}: {r8[1]}")

# R9: metadata sanity
bad_abv = bad_age = bad_meta = 0
for eid, meta_json in cur.execute(
    "SELECT evidence_id, metadata_json FROM staging_editorial_reviews"
):
    if not meta_json:
        continue
    try:
        meta = json.loads(meta_json)
    except Exception:
        bad_meta += 1
        add("R9", f"unparseable metadata: {eid}")
        continue
    abv = meta.get("abv")
    if abv is not None and not (0 < abv <= 100):
        bad_abv += 1
        add("R9", f"abv out-of-range {abv}: {eid}")
    age = meta.get("age")
    if age is not None and not (0 < age <= 100):
        bad_age += 1
        add("R9", f"age out-of-range {age}: {eid}")

# R10: dates
for eid, d in cur.execute(
    "SELECT evidence_id, published_date FROM staging_editorial_reviews"
):
    if d is not None and (len(d) != 10 or d[4] != "-" or d[7] != "-"):
        add("R10", f"non-ISO date {d!r}: {eid}")

total = cur.execute("SELECT COUNT(*) FROM staging_editorial_reviews").fetchone()[0]
scored = cur.execute(
    "SELECT COUNT(*) FROM staging_editorial_reviews WHERE score_value IS NOT NULL"
).fetchone()[0]
zero_vec = cur.execute(
    "SELECT COUNT(*) FROM staging_editorial_reviews "
    "WHERE flavor_vector_json LIKE '%0.0,%' OR flavor_vector_json = '{}'"
).fetchone()[0]
conn.close()

print(f"=== QA AUDIT: {DB.name} ===")
print(f"rows={total} scored={scored} ({(scored/total*100) if total else 0:.1f}%)")
for rule in sorted(violations):
    n = {"R1": "R4 [0,1]", "R2": "7-axis exact", "R3": "dupe",
         "R4": "null names", "R5": "score norm", "R6": "evidence_id",
         "R7": "authority", "R8": "provenance", "R9": "metadata",
         "R10": "dates"}[rule]
    lines = violations[rule]
    status = "PASS" if not lines else f"FAIL ({len(lines)} shown / maybe more)"
    print(f"  {rule} {n:12s} {status}")
    for ln in lines:
        print(f"      - {ln}")

has_fail = any(violations[r] for r in violations)
print("\nRESULT:", "FAIL" if has_fail else "ALL CHECKS PASS")
sys.exit(1 if has_fail else 0)
