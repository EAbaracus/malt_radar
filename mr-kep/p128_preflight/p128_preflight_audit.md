# P128 Preflight Audit — SMWS USA Staging Promotion (READ-ONLY, Gate Pre-Check)

- audit_version: P128-PREFLIGHT-1
- date_utc: 2026-07-16
- mode: READ-ONLY (gate via `get_read_connection` / `?mode=ro` + `query_only=ON`); zero DB mutation
- target_of_audit: P127.5 outputs (`mr-kep/p127_5_smws/`) + staging (`mr-kep/p119_6/staging_smws_tasting_notes.csv`) + production.db + knowledge.db
- decision_under_test: D1 target=`knowledge.db` / D2 reuse `official_source_references` / D3 consensus-via vectors / D4 726 promote + 77 review + 0 create

## Reference hashes (read-only snapshot; unchanged by this audit)
| artifact | sha256 | size | note |
|---|---|---|---|
| staging_smws_tasting_notes.csv | `10113e53…78d5a0f` | 651,336 | matches P127.5 manifest recorded hash (staging untouched since P127.5) |
| production.db (`output/import/`) | `d842b118…ec62961` | 12,664,832 | matches P127.5 manifest recorded hash |
| knowledge.db (`output/import/`) | `e3b0c442…7852b855` | **0** | EMPTY — no tables |
| knowledge.db (`mr-kep/p102_bootstrap/`) | `e3878743…fe6cd72` | 12,214,272 | seed used for table introspection only |
| canonical_vectors_staging.csv | `0da14b28…3d82f15` | 27,904 | 792 rows |
| p120 promotion_ready.csv | `0801f46a…18ce84f4` | 56,698 | 790 rows |

> Staging + production.db hashes equal the P127.5 manifest's recorded hashes → both inputs are byte-stable; no silent drift. This audit performed no writes.

---

## PART A — P127.5 Output Verification (Read-Only Reference Check)

### A.1 MERGE 726 linkage source — CONFIRMED as pre-existing mapping, NOT resolver fuzzy match
The P127.5 `resolver_manifest.md` states the similarity algorithm is:
> "SMWS code = exact identity token (deterministic join to production.db `flavor_evidence.smws_code` / `promotion_ready.smws_code`)"

Evidence:
- `production.db.flavor_evidence` has **791** rows, all carrying `smws_code` + `whisky_id`, and **791/791** of those `whisky_id` values exist in `production.whiskies` (FK valid).
- `smws_merge_candidates.csv`: **726/726** rows carry a `matched_whisky_id` that exists in `production.whiskies` → **726/726 FK valid, 0 orphans**.
- The `reason` column on every merge row reads "smws_code linked to existing whisky_id in production.db (flavor_evidence/promotion_ready)" — i.e. the linkage is the pre-existing `flavor_evidence` mapping, deterministically re-used, not P127's fuzzy resolver producing new matches.

**Conclusion (A.1):** "Existing whisky_id link confirmed" — the 726 MERGE links come from the pre-built `flavor_evidence` mapping, consistent with the manifest. The 7-stage fuzzy resolver contributed **0** new linkages for the MERGE bucket (it only populated the AMBIGUOUS fallback candidates).

### A.2 CREATE = 0 verification
- `staging_smws_tasting_notes.csv` carries **no** `whisky_id` column (columns: `id,source,file_name,cask_no,distillery,product_name,age,abv,region,cask_type,flavour_profile,tasting_notes_raw,extraction_confidence,review_status`). Therefore the task's suggested SQL `SELECT COUNT(*) FROM staging WHERE whisky_id IS NULL` is **not executable as written** — the column does not exist on the staging table.
- The relationship "all 803 source rows have a resolved whisky_id" is **only** true for the 726 MERGE subset (via `flavor_evidence`); the 77 AMBIGUOUS rows have **no** `matched_whisky_id` (their `candidate_*` columns are fuzzy name guesses, not identities).
- **Conclusion (A.2):** CREATE=0 is internally consistent (no net-new `whisky_id` minted), but the premise "all 803 have resolved whisky_id" is **FALSE** — 77 rows are unresolved. No "CREATE candidates missed" warning is warranted (0 CREATE is the correct disposition); however the task's framing overstates resolution coverage.

### A.3 Number-chain verification
| transition | value | evidence |
|---|---|---|
| input rows | 803 | logical CSV row count |
| distinct cask_no (smws_code) | 797 | 6 codes appear twice (`5.42, 50.62, 64.60, 73.x` group etc.) → 6 extra rows |
| unique entities (group by cask_no,product_name,distillery,bottler) | 798 | staging confidence_distribution.md states 798 (797 codes + 1 boundary case where a duplicated code spans a distinct product/distillery group) |
| output = 726 MERGE + 77 AMBIGUOUS + 0 CREATE | 803 ✓ | sum check passed |

> Note: merge CSV shows **724** distinct `smws_code` (2 codes, `100.12` and `094.4`, each appear in 2 rows → same `whisky_id`, same name → safe dedupe within MERGE). Ambiguous shows 73 distinct codes / 77 rows. Total distinct codes across both = 797 ✓ (matches A.3).

### A.4 Definition of 792 and 790
**canonical_vectors_staging.csv = 792 vectors**, columns `smws_code,smoky,peaty,sherry,fruity,spicy,sweet,rich`.
- Normalized-code overlap with staging: **787** staging codes have a vector; **4** vector codes are unmapped to staging (`048.08, 100.08, 123.03, 123.04`); **10** staging codes have no vector (incl. `G3`, `G4.6` — non-standard prefixes). So the "11-row gap" in the task is actually: vectors lead staging by 4, staging leads vectors by 10 → net 792 vs 803 diff = 11, but it is **not** 11 missing; it is a 14-code asymmetric gap driven by code-format mismatch (zero-padding) and 2 Special/G codes.
- **Mapping is 1:1** (792 distinct vector codes, 797 distinct staging codes). Not 1-N.

**p120 promotion_ready.csv = 790 rows**, columns `smws_code,whisky_id,name`.
- Distinct (normalized) = 790; **67** p120 codes are NOT in staging (they are the same zero-padded `001.185`-style codes whose unpadded staging twins were filtered) and **74** staging codes are absent from p120. The 13-row filter difference (803→790) is explained by p120 being built from a code-normalized, de-duplicated set that dropped 6 duplicate-code extras + boundary cases, **not** by content quality filtering. p120 `whisky_id` FK valid: **790/790**.
- p120 is a *downstream* artifact (P120), not an input to this promotion; it corroborates that 790 codes resolve to production UUIDs.

---

## PART B — 726 MERGE Promote-Ability Control

### B.1 Whisky_ID validation (FK)
- `SELECT COUNT(*) FROM staging WHERE bucket='MERGE' AND whisky_id NOT IN (SELECT whisky_id FROM whiskies)` — **not executable** (no `bucket`/`whisky_id` columns on staging).
- Correct form (joined from merge CSV): **726/726** `matched_whisky_id` ∈ `production.whiskies` → **0 orphan whisky_id**. PASS.

### B.2 Source citation readiness (P128 C1 — FAIL)
- P128 C1 requires every promoted row to carry a `source_citation_id`.
- **None** of the staging CSV, merge CSV, or ambiguous CSV carries a `citation_id` / `source_ref` / `source_citation_id` column.
- `production.official_source_references` (96 rows) contains **0** SMWS-source entries (all 96 are `official_facts` brand-website entries for `whisky` entities, e.g. Laphroaig/Glenlivet/Macallan `cask_type` facts).
- **Conclusion (B.2): citation gap = 726/726 MERGE rows lack any citation reference.** P128 C1 is **NOT met**. → CRITICAL BLOCKER for promotion.

### B.3 NULL field summary (data quality)
Join merge `smws_code` → staging `cask_no` (normalized):
| field | null in 726 MERGE | % |
|---|---|---|
| distillery | 349 | 48.1% |
| flavour_profile | 653 | **89.9%** |
| product_name | 0 | 0.0% |

- P128 merge policy + AGENTS.md require nulls to be explicit (`null`, never invented). 653/726 MERGE rows have no `flavour_profile` → vector promotion onto those rows has **no flavor ground truth** to merge against. This is the blocker the P127.5 eligibility report already flagged ("727 NULL flavour_profile").
- **Handling:** per AGENTS.md, these must route to `review_status` / `staging_manual_review_queue`, NOT silent default. 653 MERGE rows are therefore **promotion-soft-blocked** on flavor grounds even though their FK is valid.

### B.4 Conflict risk assessment
- Duplicate `product_name` within MERGE: 165 name-groups repeat; **53** of those map one product_name to **multiple distinct `whisky_id`** (e.g. "Highlands, Speyside" → 32 ids; "Speyside, Spey" → 73 ids; "SPICY & SWEET" → 26 ids).
- These are **not** row-level conflicts (each row still has a single valid `whisky_id` via its SMWS code). They are a **semantic collision**: the staging `product_name` is a generic tasting-theme label, not a unique identifier. Risk: any downstream join on `product_name` would fan out. **No FK-level conflict; 1 semantic hazard** to document.
- Duplicate SMWS codes inside MERGE (`100.12`, `094.4`): 2 codes × 2 rows, each maps to a **single** `whisky_id` → safe, no conflict.

---

## PART C — 77 AMBIGUOUS Classification

Per `conflict_reason` + `distillery` null + `confidence_1`:
| type | count | definition | recommended action |
|---|---|---|---|
| A — multiple high-confidence matches | 2 | `confidence_1` ≥ 0.85 (2.49 @0.88, 2.54 @0.85) | manual_merge_review |
| B — low fuzzy score, contextually plausible | 35 | fuzzy <0.85, has distillery context | manual_review |
| C — NULL distillery/flavour prevents blocking | 33 | `distillery` empty | enrich_then_review |
| D — new entity (should be CREATE?) | 7 | `no_link_in_production_db` (genuinely unmatched) | create_review |

- 40/77 AMBIGUOUS rows have NULL distillery (type C + overlap).
- 68/77 primary reason = `no_exact_smws_link`; 7 = `no_link_in_production_db`; 2 = `ambiguous_multiple_candidates`.
- **Review-queue readiness: READY.** Each row carries `candidate_1..3` + scores + reason. 7 rows (type D) are genuine new-entity candidates and should be escalated to CREATE-review, not silently dropped — this means the "CREATE=0" disposition is **revisable** for those 7 if human review confirms.

Full row-level table: `mr-kep/p128_preflight/ambiguous_classification.csv`.

---

## PART D — D1–D4 Feasibility

### D1 — Target `knowledge.db` readiness: **NOT READY (CRITICAL)**
- `output/import/knowledge.db` is **0 bytes, 0 tables** → no `canonical_vectors`, no `citations`, no `official_source_references`. Target is empty.
- `mr-kep/p102_bootstrap/knowledge.db` (the only DB with those tables) has:
  - `canonical_vectors` (3,077 rows): cols `vector_id,consensus_id,smoky,peaty,fruity,sweet,spicy,maritime,sherry` — **no `smws_code`, no `rich`**.
  - `citations` (13,133 rows): cols `citation_id,version_id,page_number,chunk_id,raw_text,source_hash` — **no `source_key`, no `source_citation_id`**.
  - `official_source_references`: **ABSENT**.
- **Conclusion:** D1 as specified ("target = knowledge.db") cannot proceed — the chosen target file is empty and lacks all three required tables; the only populated `knowledge.db` has an **incompatible schema** (no `smws_code`/`rich` on vectors; no `source_key`/`source_citation_id` on citations; no `official_source_references`). Requires DDL bootstrap of `output/import/knowledge.db` (or re-targeting) before any promotion.

### D2 — `official_source_references` reuse: **PARTIAL (ALTER needed)**
- Production table (14 cols): `ref_id,entity_type,entity_id,source_category,source_name,source_url,source_domain,field_name,field_value,confidence,retrieved_at,license_risk,copyright_risk,created_at`.
- It has **no SMWS-specific columns** and currently holds 0 SMWS rows. Reusable as a *table*, but to record an SMWS USA source chain you must either (a) insert rows using existing generic columns (`entity_type='whisky'`, `entity_id=<whisky_id>`, `source_name='SMWS USA'`, `field_name=<flavour_profile|tasting_note>`, `field_value=<...>`), or (b) `ALTER TABLE` to add `smws_code`/`source_citation_id`. No schema-breaking incompatibility, but **no citation rows exist yet** → C1 still unmet regardless.

### D3 — Consensus-via vector load: **INFEASIBLE (CRITICAL)**
- P128 policy: "vectors never direct — only via `consensus_nodes`".
- `consensus_nodes` (3,077 rows) cols: `consensus_id,whisky_id,algorithm_version,status`; `whisky_id` values are `W000001`-style, **NOT** production UUIDs.
- MERGE `matched_whisky_id` values are production UUIDs (e.g. `21e7ffc0-…`). A sampled production UUID returns **0** matches in `consensus_nodes.whisky_id`; a sampled `W000001` returns 1 match in `production.whiskies` (the ID spaces are different, not merely formatted).
- Because there is **no bridge column** (production.whiskies has no consensus/W-id; `canonical_vectors` links via `consensus_id`→`consensus_nodes`, not via SMWS code), the 726 MERGE vectors **cannot be derived through `consensus_nodes`** without first building a UUID↔W-id crosswalk that does not currently exist.
- **Conclusion:** D3 is not feasible with current data. Either (a) build the crosswalk (new pipeline work, out of scope for preflight), or (b) the 726 MERGE vectors must be loaded against `canonical_vectors` keyed by `smws_code` directly — which P128 §5 forbids. Blocked.

### D4 — Promotion count split: **PARTIALLY READY**
- 726 MERGE / 77 AMBIGUOUS / 0 CREATE split is well-defined and the CSVs can be split accordingly.
- **But** two sub-issues: (1) 653/726 MERGE rows lack `flavour_profile` → flavor-merge has no ground truth; (2) 7 of the 77 AMBIGUOUS are type-D new-entity candidates that may need CREATE, so "0 CREATE" may not hold after human review.
- Staging CSV transform into 3 buckets is mechanically possible; semantic readiness is gated by B.2/B.3/D1/D3.

---

## VERDICT: **NO-GO**

### GO criteria
| # | criterion | result |
|---|---|---|
| 1 | 726 MERGE whisky_id valid (FK) | ✅ PASS (726/726) |
| 2 | 726 MERGE citation complete (P128 C1) | ❌ FAIL (0/726 carry a citation ref; osr has 0 SMWS rows) |
| 3 | 77 AMBIGUOUS classified + review-ready | ✅ PASS (typed A/B/C/D, CSV emitted) |
| 4 | D1–D4 feasibility + DDL identified | ❌ 2 CRITICAL blockers (D1 empty target; D3 no ID bridge) |

### Blockers (must clear before gate transaction)
- **B1 (CRITICAL):** `output/import/knowledge.db` is empty (0 bytes). No `canonical_vectors`/`citations`/`official_source_references`. D1 cannot proceed.
- **B2 (CRITICAL):** No UUID↔`consensus_nodes` (W-id) crosswalk exists → D3 consensus-via vector derivation infeasible; P128 §5 direct-load path is forbidden.
- **B3 (HIGH):** P128 C1 unmet — 726/726 MERGE rows have no `source_citation_id`; `official_source_references` holds 0 SMWS entries.
- **B4 (HIGH):** 653/726 (89.9%) MERGE rows have NULL `flavour_profile` → no flavor ground truth to merge; promotion-soft-blocked per AGENTS.md review routing.
- **B5 (MED):** Staging/merge/ambiguous CSVs lack `bucket`/`whisky_id`/`source_citation_id` columns the task's SQL presumes — SQL must be re-expressed as join logic (done in this audit).

### What is GREEN (can proceed once blockers cleared)
- Bucket coverage 100% (726+77+0=803, no overlap, 0 orphans — verified).
- MERGE FK integrity perfect (726/726).
- AMBIGUOUS review queue fully prepared.
- ID-space for production promotion (if re-targeted to production.db via `flavor_evidence`) is sound.

### Required DDL / pipeline work before gate (see `ddl_prerequisite_checklist.md`)
1. Bootstrap `output/import/knowledge.db` (or re-target) with `canonical_vectors`(+`smws_code`,+`rich`), `citations`(+`source_key`,+`source_citation_id`), `official_source_references`.
2. Build UUID↔W-id crosswalk (production.whiskies ↔ bootstrap.consensus_nodes) — or obtain policy waiver for direct `smws_code`-keyed vector load.
3. Generate 726 `official_source_references` SMWS rows + attach `source_citation_id` to every MERGE row (C1).
4. Decide handling of 653 NULL-`flavour_profile` MERGE rows (review vs default) and 7 type-D AMBIGUOUS (CREATE-review).
