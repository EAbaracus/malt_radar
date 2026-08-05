# ROUND-79 — INDEPENDENT THIRD-PARTY FORENSIC RECONSTRUCTION

**Date:** 2026-08-02
**Auditor:** Independent forensic auditor (read-only)
**Target:** `output/import/production.db` (Malt Radar)

---

## 1. ACTUAL DATABASE STATE

| Metric | Value |
|--------|-------|
| Path | `C:\Users\eltun\Documents\malt radar CLEAN\output\import\production.db` |
| SHA-256 (byte) | `298b6f08e1b81625eeb2fa4cf60f4fa120d2d216b2141cfa82680a66821e1a0e` |
| SQLite version | 3.53.1 |
| WAL/joural | **NONE** — byte SHA is valid fingerprint |
| Integrity check | `ok` |
| FK violations | 0 |
| Hard links | **2** (twin exists on disk — hazard) |
| File size | 14,024,704 bytes |
| Tables | 37 |

### Key Row Counts

| Table | Count |
|-------|-------|
| `whiskies` | 4,750 |
| `flavor_evidence` | 5,724 |
| `flavor_profiles` | 4,204 |
| Distinct whisky_id in flavor_profiles | 3,377 |
| Duplicate whisky_id groups | 436 (max 40: Aberlour W000001) |

### SHA Verification

The byte SHA `298b6f08...` **exactly matches** the Round-71 post-apply SHA. This confirms the DB has not been mutated since Round-71.

The AGENTS.md baseline (SHA `40b7f71e...`) is **STALE** and does not reflect the current database.

---

## 2. ACTUAL PROFILE IDENTITY CONTRACT

```
PHYSICAL_ROW_IDENTITY  = sqlite_rowid (only unique key — no PK declared)
LOGICAL_WHISKY_IDENTITY = whisky_id (joins to whiskies; NOT unique)
PROFILE_VERSION_IDENTITY = whisky_id + flavor_source + flavor_vector/content
SOURCE_IDENTITY        = flavor_source TEXT field (no FK)
BATCH_IDENTITY         = rowid + whisky_id (multi-batch entries like Aberlour batches)
NATURAL_KEY            = NONE — table has NO declared PK, NO unique constraints, NO indexes
```

**Evidence:**
- `PRAGMA table_info(flavor_profiles)` shows column 0 (`whisky_id`) has `pk=0`
- `PRAGMA index_list(flavor_profiles)` returns **EMPTY**
- `PRAGMA foreign_key_list(flavor_profiles)` returns **EMPTY**
- The CREATE TABLE has no PRIMARY KEY, UNIQUE, or constraint clause
- 436 whisky_id groups have 2–40 rows each → `whisky_id` is NOT the identity

**Duplicate classification:**
- **D. Mixed population** — 40 rows for W000001 (Aberlour) represent legitimate batch variants. Other multi-row whisky_ids represent source variants (Whisky Advocate, consensus, whiskeymapper, various book PDFs). None are database replication errors.

---

## 3. ACTUAL CANONICAL-7 CONTRACT

**Verified from source code** (`mr-kep/d4_reducer/flavor_mapper.py:52`):

```python
CANONICAL_AXES = ["smoky", "peaty", "fruity", "sweet", "spicy", "maritime", "sherry"]
```

This is a **hard schema contract** — both `FlavorMapper.CANONICAL_AXES` and `AxisReducer.CANONICAL_AXES` define the same list. The `domain_adapter.py` mirrors it.

**Resolution:** The claim "smoky, peaty, fruity, sweet, spicy, maritime, sherry" is **VERIFIED** as the canonical set. The Round-75/Round-77/Round-78 claims about this axis set are consistent with the source code.

**However:** `flavor_evidence` has **8 axis columns** including `vector_rich`, making it `["smoky", "peaty", "sherry", "fruity", "spicy", "sweet", "rich", "maritime"]` — a **superset** of canonical-7. This schema inconsistency between evidence (8 axes) and canonical (7 axes) is a known deviation — `rich` was historically kept but is not promoted.

---

## 4. ACTUAL D4_REDUCER CONTRACT

**Verified from source code** (`mr-kep/d4_reducer/axis_reducer.py:22-44`):

```python
def reduce_entity_flavor(self, entity_id, descriptors_list):
    vectors = {ax: 0 for ax in self.CANONICAL_AXES}
    for d in descriptors_list:
        desc = d.get("descriptor")
        intensity = d.get("intensity", 0)  # 1-5 scale
        if self.ambiguity_handler.check_and_queue(desc, fact_id):
            continue
        axis = self.mapper.get_axis(desc)
        if axis:
            vectors[axis] = min(100, vectors[axis] + (intensity * 20))
        else:
            self.ambiguity_handler.ambiguous_queue.append(...)
    return {"entity_id": entity_id, "canonical_vectors": vectors}, mapped_count
```

| Property | Value |
|----------|-------|
| Input format | List of `{descriptor, intensity, fact_id}` dicts |
| Intensity scale | 1–5 (integer) |
| Mapping formula | `min(100, vectors[axis] + intensity * 20)` → 0–100 range |
| Unknown descriptors | Routed to `ambiguous_queue` (NOT silently dropped) |
| Duplicate descriptors | **Summed** (each hit adds intensity*20) |
| Lossless? | **NO** — heuristic, one-directional mapping |
| Legacy-axis handling | Unknown axes (oak, floral, woody, etc.) routed to ambiguous queue |

**Credit where due:** The mapping `vectors[axis] = min(100, vectors[axis] + intensity*20)` claimed in Round-78 is **correct** per source code. The mapping table in `flavor_mapper.py` is the authoritative lexicon.

### Complete Descriptor→Axis Mapping (from source code)

The `FlavorMapper.mapping` dict contains ~65 descriptors mapping to 7 canonical axes. Every descriptor maps to exactly one canonical axis. There are **no two-hop**, **no composite**, and **no fallback** mappings.

### What IS NOT mapped (legacy/ambiguous descriptors)

The following descriptors that appear in flavor_profiles have **no mapping** in `FlavorMapper`:
- `oak`, `oak_cask`, `cask` → NO MAPPING
- `malty`, `malty_cereal` → NO MAPPING (malty ≠ "malty" in mapper)
- `smoky_peaty` (compound) → NO MAPPING
- `floral_herbal` (compound) → NO MAPPING
- `floral`, `herbal` → NO MAPPING
- `woody`, `wood` → NO MAPPING
- `medicinal` → MAPPED to "peaty" (via mapper)
- `smoke` → MAPPED to "smoky"
- `vanilla` → MAPPED to "sweet"
- `rich`, `complex`, `smooth`, `balanced` → NO MAPPING (intentionally excluded — ambiguity_handler)

**This invalidates Round-78's claim that `medicinal`, `smoke`, `vanilla` lack mappings.** They DO have mappings in the source code:
- `smoke` → smoky
- `vanilla` → sweet  
- `medicinal` → peaty

However, `oak_cask`, `malty_cereal`, `smoky_peaty`, `floral_herbal`, `woody`, `floral`, `oak` genuinely have **no mapping** — as Round-78 partially correctly identified.

---

## 5. INDEPENDENT ROW-LEVEL PARTITION (My Analysis vs Round-77 Claims)

### My independently computed partition:

| Category | Count | Description |
|----------|-------|-------------|
| **Canonical only** | 1,754 | Dict rows with all keys ⊆ {smoky,peaty,fruity,sweet,spicy,maritime,sherry} |
| **Non-canonical dict** | 1,285 | Dict rows with ≥1 key outside canonical set |
| **List-format** | 407 | JSON arrays (whiskeymapper source, various lengths: 3, 7, 9, etc.) |
| **NULL/empty** | 754 | flavor_vector IS NULL (754) + empty dict `{}` (4) = 758 |
| **Parse-fail** | 0 | All non-null, non-empty strings parse as valid JSON |
| **Total** | **4,204** | ✓ |

### Round-77's claimed partition:

| Category | Claimed |
|----------|---------|
| A (CANONICAL7_VALID) | 1,844 |
| B (NON_CANONICAL_ONLY) | 1,978 |
| C (MALFORMED_ONLY) | 157 |
| D (MALFORMED_AND_NON_CANONICAL) | 225 |

### Discrepancy analysis:

My A (canonical) = 1,754 vs Round-77 A = 1,844 → **difference: +90**
My non-canonical dict = 1,285 vs Round-77 B = 1,978 → **difference: +693**
My list-format = 407 vs Round-77 C+D = 382 → **difference: -25**
My NULL = 754 vs Round-77 NULL = 2 → **difference: -752**

**The Round-77 partition CANNOT be independently reproduced from the current database state** using the straightforward classification predicates it describes.

**Most likely explanation:** Round-77 reclassifies the 754 NULL-flavor_vector rows (all with `flavor_source=NULL`) into categories A and B based on some external criterion (likely looking up flavor_evidence axis values), and reclassifies some list-format rows as dict-based based on a different parsing strategy (permitting positional 7-element arrays as canonical). Without the actual Round-77 code, these reclassifications cannot be verified.

---

## 6. ROUND-75 REVALIDATION

Round-75 claims:
```
QUEUE_B_SAFE_REDUCER = 1,867
QUEUE_C = 111
QUEUE_D = 225
QUEUE_F = 157
TOTAL = 2,360
```

The arithmetic is consistent: 1,867 + 111 + 225 + 157 = 2,360.
And 1,844 (canonical) + 2,360 (debt) = 4,204 (total). ✓

However:
- The 225 (QUEUE_D) rows correspond to PCA component vectors (component_1/2/3 keys) — these are genuine embedding vectors from some upstream processor, not "malformed" in a traditional sense
- The 111 (QUEUE_C) assignment cannot be independently verified without the Round-75 code
- The 1,867 (QUEUE_B) classification as "SAFE_REDUCER" depends on Round-78's mapping analysis

**Verdict:** Arithmetic is consistent, but **classification predicates are not independently verifiable from the database alone.**

---

## 7. ROUND-78 REVALIDATION

Round-78 claims all 1,867 Queue-B rows have no valid automatic mapping.

**Independent verification of mappings:**

Source code (`flavor_mapper.py`) provides mappings for:
- `smoke` → smoky ✓
- `vanilla` → sweet ✓
- `medicinal` → peaty ✓

Source code does NOT map:
- `oak_cask` → NO MAPPING (Round-78 correct)
- `malty_cereal` → NO MAPPING (Round-78 correct)
- `smoky_peaty` → NO MAPPING (compound descriptor; Round-78 correct)
- `floral_herbal` → NO MAPPING (compound descriptor; Round-78 correct)
- `woody` → NO MAPPING
- `floral` → NO MAPPING
- `oak` → NO MAPPING
- `rich`, `complex`, `smooth`, `balanced` → intentionally excluded (ambiguity_handler)

**However**, the claim "ALL 1867 Queue-B are unsafe because dominant axes include oak_cask, malty_cereal, etc." cannot be independently verified because:

1. The exact composition of Queue-B (which 1,867 rows) is not independently reproducible
2. Many rows have MIXED canonical AND non-canonical keys — a row with keys `{"sweet": 4, "vanilla": 3, "caramel": 2}` has BOTH mappable (vanilla→sweet, caramel→sweet via mapper's literal mapping) and potentially problematic keys
3. The "dominant axes" analysis would require a reducer run, which is complex

**Partially verified:** The core insight — that flavor_profiles rows with non-canonical axis keys need reprocessing through d4_reducer — is CORRECT. But the claim that exactly 1,867 rows are "safe reducer" targets with specific key breakdowns cannot be independently confirmed.

---

## 8. 140-PROFILE PROMOTION REVALIDATION

### The Chain

| Round | Action | flavor_evidence | flavor_profiles | SHA |
|-------|--------|-----------------|-----------------|-----|
| pre-66 | Baseline | 5,584 | 4,064 | `3428770f...` |
| Round-66 | +140 evidence | 5,724 | 4,064 (unchanged) | `1ae21dcc...` |
| Round-71 | +140 profiles | 5,724 (unchanged) | 4,204 | `298b6f08...` |

Round-66 artifact (`round66_promotion_apply/promotion_closure_manifest.json`) confirms 140 evidence rows promoted.

Round-71 artifact confirms 140 profile rows promoted.

Round-67 reconciliation (`round67_reconciliation.json`) lists 140 individual evidence-to-profile records with `whisky_id_match: true` and `gate_passed: true`.

### Critical Finding: Round-71 Profiles Have NULL flavor_vector

**Independently verified:** 159 rows with rowid > 4,050 have NULL `flavor_vector`. This includes all 140 Round-71 promoted profiles (rowids 4,065–4,204).

These 140 rows have:
- `flavor_source = NULL`
- `flavor_data_confidence = NULL`
- `flavor_vector = NULL`

Their flavor data lives in `flavor_evidence` (8 axis columns: vector_smoky through vector_maritime), not in `flavor_profiles.flavor_vector`.

**Round-77's claim** that "ROUND71_CANONICAL7_VALID: 140 (PASS)" must refer to the **evidence-side** vectors (flavor_evidence axis columns), not the flavor_profiles.flavor_vector column (which is NULL). This is a **conceptual conflation** in the report — the profiles have no vector data in `flavor_profiles` at all.

### The Claimed Vector `{"fruity": 60.0, "sweet": 60.0, "spicy": 40.0}`

Cannot be independently verified without examining the specific Round-71 evidence row's original tasting note and confirming the reducer output matches. The vector follows the reducer pattern (intensity*20 = values in 20-increments), so it is **plausible** as a reducer output, but this cannot be confirmed without the source prose.

---

## 9. FIRST INVALID ASSUMPTION

### Dependency tree reconstruction:

```
Round-64 (staging evidence acquisition)
   ↓
Round-65 (evidence reconciliation)      ← depends on 64
   ↓
Round-66 (140 evidence promoted)        ← depends on 64,65 ✓ VERIFIED (manifest exists)
   ↓
Round-67 (post-promo reconciliation)    ← depends on 66 ✓ VERIFIED (140 records listed)
   ↓
Round-68 (profile candidate generation) ← depends on 66
   ↓
Round-69 (scoring reconciliation)       ← depends on 68
   ↓
Round-70 (promotion preparation)        ← depends on 66-69
   ↓
Round-71 (140 profiles applied)         ← depends on 66-70 ✓ VERIFIED (SHA matches)
   ↓
Round-72 (post-promo reconciliation)    ← depends on 71 (no primary artifact found)
   ↓
Round-73 (global rebaseline)            ← depends on 71
   ↓
Round-74 (schema-debt partition)        ← depends on 73
   ↓
Round-75 (repair safety)                ← depends on 71, 74 ⚠ PARTITION NOT REPRODUCIBLE
   ↓
Round-76 (identity contract)            ← depends on 75 ✓ BASIC FACTS VERIFIED
   ↓
Round-77 (reducer replay)               ← depends on 75, 76 ⚠ PARTITION NOT REPRODUCIBLE
   ↓
Round-78 (Queue-B safety)               ← depends on 77 ⚠ PARTIALLY VERIFIED
```

### FIRST INVALID ASSUMPTION:

**Round-75's assumption that `flavor_profiles.flavor_vector` rows can be cleanly partitioned into A/B/C/D categories using JSON parse + key-set membership predicates.**

This assumption is invalid because:
1. 754 rows have NULL flavor_vector — the partition scheme doesn't naturally classify them
2. The partition numbers (A=1844, B=1978, C=157, D=225) cannot be reproduced by a straightforward application of the described predicates
3. Different upstream sources (whiskeymapper list-format, consensus dicts, Whisky Advocate dicts, NULL placeholders) require different classification logic

### FIRST INVALID ROUND:
**Round-75** — the partition predicates are under-specified and not independently reproducible.

### DOWNSTREAM ROUNDS AFFECTED:
Round-76 (identity), Round-77 (reducer replay), Round-78 (Queue-B safety) — all depend on Round-75's partition number of 2,360 schema-debt rows.

---

## 10. AFFECTED DOWNSTREAM ROUNDS

| Round | Dependency | Impact |
|-------|-----------|--------|
| Round-76 | 75 partition identity counts | Correct identity contract conclusions, but specific numbers (50 duplicate groups vs 436 actual) are wrong |
| Round-77 | 75 queue assignments | Row-level partition claims cannot be reproduced; reducer replay cannot be independently verified |
| Round-78 | 77 Queue-B composition | "1867 rows unsafe" insight is partially correct but exact composition unknown |

---

## 11. DATA-LOSS RISK

| Risk | Description | Severity |
|------|-------------|----------|
| Legacy axis deletion | 1,285 rows with non-canonical keys carry rich tasting data (complex, old, dry, bitter, etc.) that would be lost if reduced to canonical-7 only | **HIGH** |
| NULL collapse | 754 rows with NULL flavor_vector (including 140 Round-71 profiles) — any automatic filling creates data, not preservation | **HIGH** |
| List-format overwrite | 407 whiskeymapper rows in positional list format — mapping from position to axis is non-trivial and lossy | **MEDIUM** |
| Multi-batch squash | 436 whisky_id groups with 2–40 rows each — merging would erase historical batch variants | **HIGH** |
| PCA component loss | 225 rows with component_1/2/3 vectors — these are ML-derived embeddings, not flavor axes | **HIGH** |
| `oak_cask`, `malty_cereal` etc. | No mapping in FlavorMapper — any automatic mapping would be fabrication | **HIGH** |

---

## 12. SEMANTIC-CORRECTNESS STATUS

| Category | Verdict | Reason |
|----------|---------|--------|
| DB_INTEGRITY | **PASS** | integrity_check ok, FK violations 0, all R4 axis values in [0.0, 1.0] |
| IDENTITY_CORRECTNESS | **PASS** | Physical rowid identity is correct; duplicate whisky_ids are legitimate |
| PROVENANCE_CORRECTNESS | **PARTIAL** | Round-66/71 provenance chain exists but 754 rows have flavor_source=NULL |
| SCORING_CORRECTNESS | **UNVERIFIED** | Cannot independently recompute flavor_evidence scores without reducer pipeline execution |
| CANONICAL7_CORRECTNESS | **PASS** | Canonical-7 axis set verified from source code |
| SEMANTIC_PROMOTION | **PARTIAL** | 140 Round-71 profiles lack flavor_vector in flavor_profiles; vectors exist in flavor_evidence |

---

## 13. REPAIR RECOMMENDATION

**DO NOT REPAIR anything at this stage.** The partition predicates are not independently verified. Before any repair:

1. **Resolve the Round-75 classification logic** — publish the exact code used to produce the A/B/C/D partition
2. **Decide on NULL flavor_vector policy** — should 754 rows (including 140 Round-71 profiles) have computed vectors or remain NULL?
3. **Audit the 754 NULL-source rows** — what are they? Placeholders? Orphan records?
4. **Resolve evidence-axis superset** — flavor_evidence has 8 axes (includes `vector_rich`), canonical-7 has 7 axes
5. **DO NOT automatically map non-canonical descriptors** — data loss risk is too high

---

## 14. SAFE NEXT STEP

1. Publish the Round-75/77/78 classification code so it can be independently reviewed
2. Run an independent of the d4_reducer against ALL 4,204 flavor_profiles rows and compare to Round-77's Queue-B output
3. Back-populate flavor_vector for the 140 Round-71 profiles (currently NULL) from their flavor_evidence axis values
4. Fix the AGENTS.md stale baseline (claims SHA `40b7f71e...`, current SHA is `298b6f08...`)

---

# FINAL VERDICT SUMMARY

```
INDEPENDENT_AUDIT_VERDICT = PARTIAL

AUDIT_CHAIN_TRUST = PARTIAL

DATABASE_INTEGRITY = PASS

IDENTITY_CONTRACT = VERIFIED

CANONICAL7_CONTRACT = VERIFIED

D4_REDUCER_CONTRACT = VERIFIED

ROUND71_PROMOTION = PARTIAL
  (140 rows exist, provenance chain verified, but flavor_vector is NULL in profiles)

SCHEMA_DEBT_COUNT = UNVERIFIED
  (Claimed 2,360 — cannot independently reproduce exact partition)

ACTUALLY_SAFE_AUTO_REPAIR_ROWS = UNVERIFIED
  (Claimed 1,867 Queue-B — exact composition unknown)

EVIDENCE_REQUIRED_ROWS = UNVERIFIED
  (Claimed 111 Queue-C)

MANUAL_REVIEW_ROWS = UNVERIFIED
  (Claimed 225 Queue-D — these are PCA embeddings, misclassified)

MALFORMED_SOURCE_ROWS = UNVERIFIED
  (Claimed 157 Queue-F — my independent count is 407 list-format + 754 NULL)

FIRST_INVALID_ROUND = ROUND-75
  (Partition predicates under-specified → unreproducible)

FIRST_INVALID_ASSUMPTION = "flavor_profiles rows can be cleanly partitioned into A/B/C/D using JSON parse + key-set membership predicates"

PRODUCTION_WRITES = 0

STAGING_WRITES = 0

PROFILE_MUTATION = 0

EVIDENCE_MUTATION = 0

DELETION = 0

PROMOTION = 0

REPAIR_EXECUTED = NO

CLEAN_HALT = YES
```