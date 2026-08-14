# P304 â€” Certification Resolution Review

**Mode:** READ ONLY Â· Review only Â· No code changes Â· No staging/production writes Â· No promotion Â· No commit/push/tag
**Date:** 2026-07-18
**Subject candidate:** `evidence_id = EDR-b6108f7ac8d252af` (`normalized_name = "ardbeg 10"`)
**Inspection basis:** real `certification_engine/__init__.py` (262 lines) + real staging row (read-only) + P301/P302/P303 artifacts. Prior reports not trusted; facts re-derived.

---

## 1. Candidate Evidence (verified from `staging_editorial.db`, `mode=ro`)

| Attribute | Value |
|---|---|
| `evidence_id` | `EDR-b6108f7ac8d252af` |
| `raw_name` / `normalized_name` | `Ardbeg 10` / `ardbeg 10` |
| `source_id` | `whiskyfun` |
| `authority_tier` | **`T2_expert`** |
| `published_date` | `None` |
| `content_hash` | `c0f37aa9251539ac7e82e19fa3611e1235e0489ea7db7b1da1e7ccd0a33b64ff` |
| `match_status` | `unmatched` |
| `score_value` | `92.0` |
| `flavor_vector_json` | 7 canonical axes, all in [0,1] |
| `metadata_json` | distillery=Ardbeg, region=Islay, country=Scotland, abv=46.0, age=10, cask=Ex-Bourbon, nose/palate/finish present |
| `evidence_confidence` | `1.0` |
| `extraction_method` | `structured_extraction` |
| `provenance_state` | **`staging_unverified`** |
| certification (P301 report) | **`HOLD`** |

**Duplicate status:** `SemanticDeduplicator` â†’ `duplicate=False`. No duplicate.

---

## 2. Certification Engine (inspected: `certification_engine/__init__.py`)

### HARD RULES (frozen)
- `CERTIFY_MIN = 0.70`
- Per-field authority ceiling via `FIELD_CEILING`.
- Deterministic: same input â†’ same output.
- NO production write; NO AI/LLM/OCR/scraping.

### Field ceilings (`FIELD_CEILING`)
- `T1_authoritative`: `distillery_name, region, country, abv, age_statement, cask_type`
- `T2_expert`: `nose, palate, finish, flavor_axes, score`
- `T3_community`: `community_rating`

### Per-field path logic (`determine_certification_path`)
- Conflict (`merge_strategy=reject_on_conflict`) â†’ `rejected` (D)
- No/empty evidence or `conf < 0.01` â†’ `rejected` (F, Uncovered)
- `conf < CERTIFY_MIN` â†’ `rejected` (E, Below-threshold)
- Authority **satisfies** ceiling & evidence present â†’ `certified` (A)
- Authority **below** ceiling but `conf â‰¥ CERTIFY_MIN` â†’ `proposed` (C)

### Aggregate rule (`aggregate_certification`)
- any `rejected` â†’ **REJECTED**
- any `proposed` â†’ **HOLD**
- else â†’ **CERTIFIED**

### Required fields / missing-evidence requirement
A field is certified only if it appears in the evidence ledger **and** `field_value is not None` and reaches Path A. T1-ceiling fields require **T1-authority** evidence; T2-source evidence for a T1 field can never reach Path A â€” it caps at `proposed` (C), forcing aggregate `HOLD`.

---

## 3. Provenance Chain

```
source (whiskyfun fixture)
   â†“  artifact          mr-kep/fixtures/sample_whisky.json   [OK â€” real pre-produced artifact]
   â†“  extraction        extraction_execution â†’ 10 evidence records  [OK â€” State.COMPLETED]
   â†“  normalization     run.py canonicalize â†’ metadata_json + flavor vector  [OK â€” 7 axes]
   â†“  certification     certification_engine.certify â†’ HOLD  [PARTIAL â€” T1 fields = proposed]
```

**Broken / incomplete links:**
1. **Authority gap (the HOLD cause):** the extraction request carried `authority_tier = T2_expert` for a `whiskyfun` fixture. The six T1-ceiling identity fields (distillery/region/country/abv/age/cask) were therefore certified only at `proposed` (Path C), never `certified`. Aggregate â†’ **HOLD**.
2. **Provenance ratifier gap (the `staging_unverified` cause):** the runtime writes `provenance_state='staging_unverified'` by design. **No provenance-ratification step exists** anywhere in the pipeline to validate `content_hash` against the source and flip the state to `verified`. This link is structurally absent, not merely unexecuted.
3. **Master-link gap:** `match_status = unmatched` â€” the candidate is not linked to a master whisky record.

---

## 4. Promotion Blockers (classified)

| Blocker | Class | Note |
|---|---|---|
| Certification `HOLD` (T1 fields `proposed` under T2 authority) | **REQUIRES HUMAN DECISION** | Engine is correct; a human must accept the T2 evidence for T1 fields or supply T1 authority. |
| `provenance_state = staging_unverified` (no ratifier exists) | **REQUIRES HUMAN DECISION** | A human ratification/GO is the only path to `verified`; no code path performs it. |
| No sealed promotion manifest | **REQUIRES HUMAN DECISION** | Manifest spec exists (P303); must be sealed with GO. |
| No human `GO` / approval recorded | **REQUIRES HUMAN DECISION** | Absent at time of review. |
| Master-link `unmatched` | **OPEN** (non-blocking for staging) | Should be resolved before production merge; not a certification blocker. |
| Code/system defect in engine | **RESOLVED** (none found) | Engine deterministic and correct; HOLD is expected behavior for the given authority. |

No blocker is classified `OPEN` as a system failure. All gates are human-decision or procedurally pending.

---

## 5. Certification Acceptance Criteria

### `staging_unverified` â†’ `verified`
Must become true:
- `content_hash` validated against the source artifact (tamper check passes).
- Source authenticity / authority accepted by a reviewer (the `authority_tier` is acknowledged).
- A provenance-ratification step (currently **absent** from the runtime) sets `provenance_state = 'verified'`.
- *Note:* this requires adding a ratification step or a human GO that flips the flag; the runtime does not do this today.

### `HOLD` â†’ `approved`
Must become true (per engine rules):
- Every field reaches `certified` (Path A/B) â†’ aggregate becomes `CERTIFIED`; OR
- A human certification override explicitly accepts the `proposed` (Path C) T1 fields.
- Because the engine has **no built-in human-override path** (it is purely deterministic from evidence authority), the human acceptance must be recorded via the promotion manifest's `human approval = GO` gate (P303), which authorizes promoting the `proposed` fields despite HOLD.
- Minimum field confidence must remain `â‰¥ 0.70` (already satisfied: all evidence `conf â‰¥ 0.70`).

---

## 6. Final Recommendation

**READY FOR HUMAN CERTIFICATION**

Rationale:
- Evidence is **complete and confident** â€” all 10 fields present, `evidence_confidence = 1.0`, min confidence `â‰¥ 0.70`. This is **not** `WAITING FOR EVIDENCE`.
- The certification engine is **functional and deterministic**; the `HOLD` is the correct, expected result of T1 identity fields being certified under a T2 authority. There is **no system bug or missing capability** that structurally prevents certification. This is **not** `BLOCKED BY SYSTEM GAP`.
- The only remaining requirements are **human decisions**: accept the T2-evidenced T1 fields (or ratify authority), ratify provenance (`staging_unverified â†’ verified`), and record an explicit `GO`. These are exactly the actions the P303 package hands to a reviewer.

No state was changed. No promotion executed. Certification and provenance remain `HOLD` / `staging_unverified` exactly as found.
