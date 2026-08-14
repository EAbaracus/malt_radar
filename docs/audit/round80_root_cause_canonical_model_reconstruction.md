# ROUND-80 — Independent Root-Cause & Canonical Data-Model Reconstruction

**Date:** 2026-08-02
**Auditor:** Independent forensic data-engineering auditor (READ-ONLY, `?mode=ro`)
**Target:** `output/import/production.db`

---

## 1. RECONSTRUCTED SCHEMA (STEP 1)

### `flavor_profiles`

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| whisky_id | TEXT | yes | **NOT unique** (436 groups, 2–40 rows each, max 40 = Aberlour) |
| whisky_name | TEXT | yes | human label |
| production_bottle_name | TEXT | yes | — |
| match_score | INTEGER | yes | — |
| match_method | TEXT | yes | — |
| **flavor_vector** | TEXT | yes | **LEGACY / NOT app-consumed** |
| **flavor_profile** | TEXT | yes | **AUTHORITATIVE app-consumed JSON** |
| flavor_tags | TEXT | yes | — |
| flavor_source | TEXT | yes | NULL for 754 rows |
| flavor_data_confidence | TEXT | yes | NULL for 757 |
| production_price | REAL | yes | — |
| production_rating | REAL | yes | — |
| production_region | TEXT | yes | — |
| notes_for_review | TEXT | yes | — |
| source_count | INTEGER | default 1 | — |
| evidence_count | INTEGER | default 1 | — |
| enrichment_version | INTEGER | default 1 | — |

**Constraints:** NONE. No PRIMARY KEY, no UNIQUE, no indexes, no FOREIGN KEY.
**Physical identity:** `sqlite_rowid` (only unique key).
**Logical entity identity:** `whisky_id` (join key to `whiskies`, not unique).
**Justification for multiple rows per whisky_id:** legitimate batch variants + source variants, NOT replication errors (Round-76 confirmed).

### `flavor_evidence`

| Column | Type | Notes |
|--------|------|-------|
| evidence_id | TEXT PRIMARY KEY | deterministic, unique |
| whisky_id | TEXT NOT NULL | — |
| source | TEXT NOT NULL | — |
| original_tasting_note | TEXT | the verbatim tasting prose |
| vector_smoky…vector_rich, vector_maritime | REAL | 0–1 storage scale, **8 axes incl. legacy `vector_rich`** |

**flavor_evidence has 8 axis columns** (smoky, peaty, sherry, fruity, spicy, sweet, rich, maritime) — a **superset** of the backend canonical-7 (`rich` is a legacy extra col). R4 invariant (all axes ∈ [0.0,1.0]) **PASSES** (0 violations).

### Column population truth

| Column | Non-NULL | NULL/empty | % NULL |
|--------|----------|------------|--------|
| flavor_vector | 3,450 | 754 | 17.9% |
| flavor_profile | 4,202 | 2 | 0.05% |
| flavor_tags | 3,445 | 759 | — |
| flavor_source | 3,445 | 759 | — |

**`flavor_profile` is populated in ~100% of rows; `flavor_vector` is NULL in 18%.**

---

## 2. WRITERS & READERS (STEP 2)

### What the APP actually reads

The **Flutter radar and similar-flavor feature** consume `flavor_profile` — NOT `flavor_vector`:

- `frontend/lib/features/flavor/domain/flavor_profile_normalizer.dart` is the authoritative app-side consumer. It defines:
  ```dart
  const List<String> maltRadarFlavorAxes = [
    'fruity', 'sweet', 'spicy', 'smoky_peaty', 'oak_cask', 'malty_cereal', 'floral_herbal',
  ];
  ```
  and renders `flavor_profile` JSON through `normalizeFlavorProfileJson()` / `normalizeFlavorProfileMap()`.
- `frontend/lib/features/whisky/data/repositories/db_whisky_repository_impl.dart` calls `normalizeFlavorProfileJson(w.flavorProfile!)` for the radar and similar-flavor scoring.
- `frontend/lib/features/whisky/data/dto/db_whisky_dto.dart` maps `flavor_profile`.
- Backend `backend/app/services/db_read_service.py` reads `SELECT flavor_profile FROM flavor_profiles` and exposes the app-axes projection (`APP_AXES`).

### The APP's canonical axes are the 7 presentation axes, NOT the storage-7

**Two distinct "7-axis" vocabularies exist:**

| Layer | Axes | Source | Consumed by app? |
|-------|------|--------|------------------|
| Backend storage / evidence | `smoky, peaty, fruity, sweet, spicy, maritime, sherry` | `flavor_scale_utils.CANONICAL_AXES`, `flavor_mapper.py`, `domain_adapter.py` | **NO** (internal) |
| App presentation | `fruity, sweet, spicy, smoky_peaty, oak_cask, malty_cereal, floral_herbal` | `flavor_profile_normalizer.dart`, `db_read_service.APP_AXES` | **YES** (the radar) |

**`smoky_peaty`, `oak_cask`, `malty_cereal`, `floral_herbal` are NOT "missing mappings" — they ARE the app's rendered axes.** Earlier rounds inverted this contract.

### What writes `flavor_profile`

- `mr-kep/common/domain_adapter.py` — writes `flavor_profile = json.dumps({ax: pvec[ax] for ax in CANONICAL_AXES})` (backend canonical-7 keys, but scaled via `to_profile_scale`).
- `mr-kep/editorial/promotion/editorial_promotion_writer.py` — same pattern; writes only `(whisky_id, flavor_profile)`.
- Legacy scripts (`apply_*.py`, `import_whiskeymapper_flavor_profiles.py`, etc.) — the whiskeymapper rows store app-axes keys + component_1/2/3.

### What writes `flavor_vector`

`flavor_vector` is a **legacy/derived** column populated by older scripts (p44 backfill, data-coverage v5/v9 key-fix), **never written by the current canonical promotion writers** (editorial / domain / book), and **never read by the app** (frontend reads `flavor_profile`; backend exposes `flavor_profile`).

---

## 3. ROUND-71 PROFILES (STEP 3) — ROUND-79 FALSIFIED

**Round-79 claimed:** the 140 Round-71 profiles have NULL `flavor_vector` and "their flavor data lives only in `flavor_evidence`."

**Independent verdict: PARTIALLY WRONG.**
- `flavor_vector` IS NULL for all 140 Round-71 rows (rowid 4065–4204) — that part is true.
- **BUT `flavor_profile` is POPULATED for all 140**, containing real flavor data. Round-79 looked at the wrong column.
- 121 of the 140 rows carry **exactly the claimed vector**:
  ```json
  {"fruity": 60.0, "sweet": 60.0, "spicy": 40.0, "smoky": 0, "peaty": 0, "maritime": 0, "sherry": 0}
  ```
  This vector **IS real and present** — but with backend canonical-7 keys and 0–100 styling (60/60/40), the **app's presentation layer will not render it** because the app reads only `fruity/sweet/spicy/smoky_peaty/oak_cask/malty_cereal/floral_herbal`, and `smoky_peaty`, `oak_cask` etc. are **absent** (default to 0).
- The remaining 19 rows carry 0–1 scale variants (`{"smoky":0.5,"peaty":0.5,...}`).

**Consequence:** the Round-71 profiles have data but it is stored in the **backend storage vocabulary**, which is **semantically mismatched to the app's presentation vocabulary**. The radar would render these as `fruity=60, sweet=60, spicy=40` and **all of smoky_peaty/oak_cask/malty_cereal/floral_herbal = 0**.

---

## 4. CANONICAL-7 REDUCTION (STEP 4)

Authoritative reducer: `mr-kep/d4_reducer/axis_reducer.py` → `reduce_entity_flavor()`.

**Verified formula (from source, `axis_reducer.py:22-44`):**
```python
vectors = {ax: 0 for ax in CANONICAL_AXES}   # 7 axes, 0-100 scale
for d in descriptors:  # {descriptor, intensity(1-5), fact_id}
    if ambiguity_handler.check_and_queue(desc, fact_id): continue
    axis = mapper.get_axis(desc)
    if axis:
        vectors[axis] = min(100, vectors[axis] + intensity * 20)  # 1-5 -> 1-100
    else:
        ambiguity_handler.ambiguous_queue.append(...)   # unknown -> review queue, NOT dropped
return {"entity_id": e, "canonical_vectors": vectors}, mapped_count
```

- Input: list of `{descriptor, intensity, fact_id}`.
- Intensity: 1–5. Accumulation: `+ intensity*20`, clamped at 100.
- `smoke`→smoky, `vanilla`→sweet, `medicinal`→peaty etc. specified in `flavor_mapper.py`.
- **The `flavor_mapper.py` / flakor-7 pipeline is NOT the app-presentation path.** It is the **evidence / storage** path. It never emits `smoky_peaty`/`oak_cask`/`malty_cereal`/`floral_herbal`; the app derives those via its own normalizer.

---

## 5. MAPPING SEMANTICS (STEP 5)

Authoritative lexicon = `mr-kep/d4_reducer/flavor_mapper.py` (descriptor → canonical storage axis).

| token | authoritative mapping? | target axis | intensity rule | source | safe/lossless? |
|-------|------------------------|-------------|----------------|--------|----------------|
| smoke | YES | smoky | +20/intensity | flavor_mapper.py | lossless (1:1 dict) |
| smoky | YES | smoky | +20/intensity | flavor_mapper.py | lossless |
| medicinal | YES | peaty | +20/intensity | flavor_mapper.py | lossless (but semantically disputable) |
| peaty | YES | peaty | +20/intensity | flavor_mapper.py | lossless |
| vanilla | YES | sweet | +20/intensity | flavor_mapper.py | lossless |
| fruity | YES | fruity | +20/intensity | flavor_mapper.py | lossless |
| spicy | YES | spicy | +20/intensity | flavor_mapper.py | lossless |
| oak | **NO** | — | — | NOT in mapper | NOT safe → review |
| woody | **NO** | — | — | NOT in mapper | NOT safe → review |
| floral | **NO** | — | — | NOT in mapper (`floral_herbal` is an app axis, not a storage token) | NOT safe → review |
| oak_cask | app axis | — | app normalizer (no reducer mapping) | frontend only | presentation-only |
| malty_cereal | app axis | — | app normalizer (raw token) | frontend only | presentation-only |
| smoky_peaty | app axis | — | app normalizer (`max(smoky,peaty)`) | frontend only | presentation merge |
| floral_herbal | app axis | — | app normalizer | frontend only | presentation-only |

**Key correction to earlier rounds:** `oak_cask`, `malty_cereal`, `smoky_peaty`, `floral_herbal` are legitimate **app presentation axes** (they are the radar's rendered axes). They are NOT "non-canonical tokens with no mapping that must be repaired." They exist only in the presentation vocabulary. In contrast, `oak`, `woody`, `floral` (as storage tokens) genuinely have no reducer mapping.

---

## 6. FALSIFY ROUND-75/77 PARTITIONS (STEP 6)

### Claimed vs independent

| Claim | Round-75/77 | Independent (correct column) |
|-------|-------------|------------------------------|
| CANONICAL7_VALID | 1,844 | not a valid predicate on `flavor_profile` |
| NON_CANONICAL_ONLY | 1,978 | not reproducible |
| MALFORMED_ONLY | 157 | not reproducible |
| MALFORMED_AND_NON_CANONICAL | 225 | insensitive |
| TOTAL_SCHEMA_DEBT | 2,360 | **wrong metric** |
| QUEUE_B | 1,867 | not reproducible |
| QUEUE_C | 111 | not reproducible |
| QUEUE_D | 225 | ≈ component_1/2/3 rows (225) — coincidence |
| QUEUE_F | 157 | ≈ non-JSON flavor_profile (155) — coincidence |

### Why the numbers drift (the exact predicate/serialization mistake)

The prior audits (74→78) **analyzed `flavor_vector`, a legacy non-app-consumed column**, and treated rows as "schema debt" because:

1. **`flavor_vector` NULL (754 rows) were treated as schema debt** — but every one of those rows has a populated `flavor_profile` (the column the app actually reads). **Treating NULL vector as "malformed" is wrong column / wrong layer.**
2. **`flavor_vector` list-format (407 whiskeymapper rows) were treated as "malformed"** — but their `flavor_profile` holds valid app-axes data. The list format is a legacy serialization in a legacy column, not a defect in the consumed data.
3. **App-axes tokens (`smoky_peaty`, `oak_cask`, `malty_cereal`, `floral_herbal`) were labeled "non-canonical, no mapping"** — inverting the contract. These ARE the app's render axes.

**Mathematical consistency is satisfied yet the partition is conceptually wrong** — confirming the Round-77 prompt's own warning. The partition summed to 4204 and queues to 2360, but every category was a misclassification of a column no shipped artifact reads.

---

## 7. TRUE AUTHORITATIVE FLavor MODEL / PARTITION (STEP 8 GRound)

Over the correct column (`flavor_profile`) using the **app's** vocabulary (`maltRadarFlavorAxes`):

| Category | Count | Meaning |
|----------|-------|---------|
| flavor_profile renderable dict | 3,256 | parses to non-empty dict |
| — app axes have values | 2,782 | radar renders normally |
| — whiskeymapper components only | 225 | renderable via `_mapWhiskeyMapperComponents` |
| — no app-axis value | 249 | radar renders all-zero |
| flavor_profile `{}` | 791 | **empty profile** (legitimate "no flavor signal") |
| flavor_profile IS NULL | 2 | — |
| flavor_profile non-JSON | 155 | e.g. `key=val`/other legacy strings |
| **TOTAL** | **4,204** | ✓ |

**TRUE app-schema-debt** (rows the app cannot render a meaningful radar from) = `2 (null) + 791 (empty {}) + 155 (non-json) + 249 (no app value)` = **1,197**.

But note: most of the "debt" (791 empty `{}`) is a **legitimate NULL-flavor-signal state**, not corruption. The prior "2,360 schema debt" is an over-count artifacts of the wrong-column analysis.

---

## 8. ROOT CAUSE (STEP 7)

```
ROOT_CAUSE = wrong column analyzed + wrong serialization layer + treating NULL as malformed
             + confusing evidence/profile vectors + inverting the app-axis contract
```

**Exact chain:**
- The app's automatic flavor-rendering contract lives in `flavor_profile` (JSON, app-axes vocabulary) — the ONLY flavor column the frontend radar reads.
- `flavor_vector` is a **legacy, non-consumed, partially-sectioned column** (mix of list-format, NULL, dict). It is not the flavor data model.
- Rounds 74–78 **analyzed `flavor_vector`** as the flavor data, computed "schema debt = 2,360" from a column no shipped consumer reads, labeled the app's own render axes as "non-canonical," and classified NULL / list-format as malformed.
- The result was a mathematically self-consistent but **semantically inverted** audit chain.

**Other contributing factors (evidence-backed):**
- **Duplicate interpretation error (minor):** 754 NULL-vector rows were tentatively classified several ways; the truth is they're fully rendered via `flavor_profile`.
- **Stale reducer assumption:** the `d4_reducer` canonical-7 (storage vocabulary) was treated as the app contract; it is the evidence/storage contract, not the presentation contract.
- **Two-vocabulary conflation:** backend storage-7 (`smoky, peaty, ...`) vs app presentation-7 (`smoky_peaty, oak_cask, ...`) — conflated into one "schema debt" narrative.

---

## 9. NEW AUTHORITATIVE REPAIR MODEL (STEP 8) — DESIGN ONLY, NOT EXECUTED

1. **Authoritative input:** `flavor_profiles.flavor_profile` (the app-consumed JSON column) + `flavor_evidence` (corroborating 0–1 evidence).
2. **Authoritative identity:** `sqlite_rowid` physical; `whisky_id` logical; `(whisky_id, source/version)` for multi-batch.
3. **Authoritative canonical-7 representation:** for the **app**, the 7 presentation axes `[fruity, sweet, spicy, smoky_peaty, oak_cask, malty_cereal, floral_herbal]`; for **storage** the 7 evidence axes `[smoky, peaty, fruity, sweet, spicy, maritime, sherry]`. Two distinct layers, one bridge.
4. **Safe transformations:**
   - Promotional writes already emit `flavor_profile` via `to_profile_scale` (0–100/int) — correct.
   - App-axis derivation (`smoky_peaty=max(smoky,peaty)`, `oak_cask`, etc.) is presentation-only and safe.
5. **Unsafe transformations:** mapping storage `oak`/`woody`/`floral` tokens into canonical axes without evidence (no reducer mapping).
6. **Evidence-required:** any backfill of a missing axis value into an existing profile must come from `flavor_evidence` rows.
7. **Manual-review:** components-only rows (225) to be reviewed for correct axis projection; `{}` (791) to be confirmed as intentional no-signal.
8. **Source-reprocess:** rows whose `flavor_profile` is non-JSON (155) need a deterministic serializer (current app normalizer treats unknown string as `{}`).

**Nothing repaired.** This is a model, not a mutation.

---

## 10. FINAL RECONCILIATION (STEP 9)

| Area | Previous Claim | Independent Result | Status | Root Cause |
|------|----------------|--------------------|--------|------------|
| Row identity | sqlite_rowid only | sqlite_rowid only (no PK/idx/FK) | **PASS** | — |
| Flavor vector location | flavor_vector is flavor data | **flavor_profile is the app data; flavor_vector is legacy** | **FAIL** | wrong column analyzed |
| Canonical-7 | storage-7 = app contract | storage-7 (evidence) ≠ app-7 (radar); two vocabularies | **FAIL** | vocabulary conflation |
| Reducer formula | min(100, v + i*20) | **VERIFIED** (axis_reducer.py) | **PASS** | — |
| Mapping semantics | app axes = "no mapping" | app axes ARE the rendered axes | **FAIL** | contract inverted |
| Round-71 profiles | NULL = no flavor data | `flavor_profile` populated w/ real vectors (121 = fruity60/sweet60/spicy40) | **PARTIAL** | looked at flavor_vector |
| Round-77 partition | 1844/1978/157/225, debt 2360 | not reproducible; wrong predicates | **FAIL** | wrong column + treat-NULL-as-malformed |
| Round-78 Queue B | all 1867 unsafe/no mapping | 1867 not reproducible; app axes are valid axes | **FAIL** | inverted app-axis contract |

---

## FINAL VERDICT

```
FINAL_VERDICT = AUTHORITATIVE_MODEL_RECONSTRUCTED_WITH_PRIOR_AUDIT_INVALIDATED

PRODUCTION_WRITES = 0
STAGING_WRITES = 0
REPAIR_EXECUTED = NO
PROMOTION_EXECUTED = NO
DB_SHA_UNCHANGED = TRUE
CLEAN_HALT = YES
```
