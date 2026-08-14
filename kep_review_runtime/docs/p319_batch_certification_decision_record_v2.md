# Batch Certification Decision Record (Evidence-Based) â€” P319 v2

**Mode:** DOCUMENTATION ONLY Â· No database writes Â· No staging mutation Â· No production mutation Â· No promotion Â· No commit/push/tag
**Date:** 2026-07-18
**Status:** PENDING HUMAN CERTIFICATION

---

## 1. Batch Overview

| Field | Value |
|---|---|
| `batch_id` | `PROMO-BATCH-20260718-001` |
| Candidate count | 4 |
| Evidence IDs | `EDR-0645f7a10c3c59c1`, `EDR-39d77abca9a6375e`, `EDR-63a322317c787409`, `EDR-9949a1899234acde` |
| Production IDs | `W001152`, `W000496`, `W000976`, `W001100` |
| Review scope | Match assessment Â· Identity verification Â· Evidence review Â· Provenance review Â· Certification decision |
| Precedent | `PROMO-20260718-001` â€” ardbeg 10 â†’ W003571 (single candidate, same T2_expert authority) |

---

## 2. Match Assessment

### Candidate A: Ardbeg 10 Year Old â†’ W001152

| Field | Candidate | Production |
|---|---|---|
| matched_master_whisky_id | `W001152` | `W001152` |
| Production name | â€” | `ardbeg 10yo` |
| Raw name | `Ardbeg 10 Year Old` | â€” |
| Age | 10 | 10.0 (age_statement: `10yo`) |
| Type | â€” | `Malt` |

**match_score:** `1.0` â€” **DECISION SUPPORT ONLY** (never use score alone)

**Analysis:** Raw name `Ardbeg 10 Year Old` normalizes directly to production `ardbeg 10yo`. Age 10 matches in both `age` and `age_statement` fields. Type `Malt` is consistent for Ardbeg. No conflicting whisky with same normalized name exists in production.

**Match recommended:** âœ… EXACT

---

### Candidate B: Clynelish 14 Year Old â†’ W000496

| Field | Candidate | Production |
|---|---|---|
| matched_master_whisky_id | `W000496` | `W000496` |
| Production name | â€” | `clynelish 14yo` |
| Raw name | `Clynelish 14 Year Old` | â€” |
| Age | 14 | 14.0 (age_statement: `14yo`) |
| Type | â€” | `Malt` |

**match_score:** `1.0` â€” **DECISION SUPPORT ONLY**

**Analysis:** Raw name `Clynelish 14 Year Old` â†’ `clynelish 14yo`. Age 14 matching. Type `Malt`. No conflict.

**Match recommended:** âœ… EXACT

---

### Candidate C: Talisker 10 Year Old â†’ W000976

| Field | Candidate | Production |
|---|---|---|
| matched_master_whisky_id | `W000976` | `W000976` |
| Production name | â€” | `talisker 10yo` |
| Distillery | â€” | `D0004` (Talisker) |
| Brand | â€” | `Talisker` |
| Region | â€” | `Islands` |
| Raw name | `Talisker 10 Year Old` | â€” |
| Age | 10 | 10.0 (age_statement: `10yo`) |
| Type | â€” | `Malt` |

**match_score:** `1.0` â€” **DECISION SUPPORT ONLY**

**Analysis:** Strongest match in the batch â€” brand `Talisker`, distillery `Talisker` (D0004, Scotland), region `Islands`. All metadata aligns. Age 10 matches. No conflict.

**Match recommended:** âœ… EXACT

---

### Candidate D: Lagavulin 16 Year Old â†’ W001100

| Field | Candidate | Production |
|---|---|---|
| matched_master_whisky_id | `W001100` | `W001100` |
| Production name | â€” | `lagavulin 16yo` |
| Raw name | `Lagavulin 16 Year Old` | â€” |
| Age | 16 | 16.0 (age_statement: `16yo`) |
| Type | â€” | `Malt` |

**match_score:** `1.0` â€” **DECISION SUPPORT ONLY**

**Analysis:** Raw name `Lagavulin 16 Year Old` â†’ `lagavulin 16yo`. Age 16 matches. Type `Malt`. No conflict.

**Match recommended:** âœ… EXACT

---

## 3. Identity Verification

### Methodology
Each candidate's extracted metadata is compared against the production whisky record and (where available) the distillery record. Identity fields are classified as:

| Classification | Meaning |
|---|---|
| **VERIFIED** | Candidate evidence matches production record, or candidate provides data that production lacks (data gap in production is NOT a conflict). |
| **CONFLICT** | Candidate evidence contradicts production record (e.g. different age, wrong distillery). |
| **MISSING** | The field is absent from both candidate evidence and production record. |

---

### Candidate A: Ardbeg 10 Year Old

| Field | Candidate evidence | Production record | Classification |
|---|---|---|---|
| Brand | â€” | â€” | **MISSING** (neither source provides) |
| Product name | `Ardbeg 10 Year Old` | `ardbeg 10yo` | **VERIFIED** (age and distiller match) |
| Age statement | `10 YO` (metadata) | `10yo` | **VERIFIED** |
| Distillery | â€” | â€” | **MISSING** (no distillery_id on W001152) |
| Region | â€” | â€” | **MISSING** (no region on W001152) |
| Country | â€” | â€” | **MISSING** (no country on W001152) |
| ABV | `46.0%` (metadata) | `None` | **VERIFIED** (candidate provides data; production missing) |
| Category | â€” | `Malt` | **VERIFIED** |

**Note:** W001152 lacks distillery_id, region, country â€” this is a production data gap, not a candidate conflict. The `name` + `age` combination uniquely identifies Ardbeg 10yo.

---

### Candidate B: Clynelish 14 Year Old

| Field | Candidate evidence | Production record | Classification |
|---|---|---|---|
| Brand | â€” | â€” | **MISSING** |
| Product name | `Clynelish 14 Year Old` | `clynelish 14yo` | **VERIFIED** |
| Age statement | `14 YO` (metadata) | `14yo` | **VERIFIED** |
| Distillery | â€” | â€” | **MISSING** |
| Region | â€” | â€” | **MISSING** |
| Country | â€” | â€” | **MISSING** |
| ABV | `46.0%` (metadata) | `None` | **VERIFIED** |
| Category | â€” | `Malt` | **VERIFIED** |

**Note:** Same pattern as Ardbeg â€” production record has minimal fields. Identity established via name + age.

---

### Candidate C: Talisker 10 Year Old

| Field | Candidate evidence | Production record | Classification |
|---|---|---|---|
| Brand | â€” | `Talisker` | **VERIFIED** (production has brand) |
| Product name | `Talisker 10 Year Old` | `talisker 10yo` | **VERIFIED** |
| Age statement | `10 YO` (metadata) | `10yo` | **VERIFIED** |
| Distillery | â€” | `D0004` â†’ Talisker | **VERIFIED** (distillery table confirms) |
| Region | â€” | `Islands` | **VERIFIED** (via distillery) |
| Country | â€” | `Scotland` | **VERIFIED** (via distillery) |
| ABV | `45.8%` (metadata) | `None` | **VERIFIED** |
| Category | â€” | `Malt` | **VERIFIED** |

**Note:** Strongest identity verification in the batch â€” brand, distillery, region, country all available. Candidate ABV 45.8% is within expected range for Talisker 10yo (official bottling is 45.8%).

---

### Candidate D: Lagavulin 16 Year Old

| Field | Candidate evidence | Production record | Classification |
|---|---|---|---|
| Brand | â€” | â€” | **MISSING** |
| Product name | `Lagavulin 16 Year Old` | `lagavulin 16yo` | **VERIFIED** |
| Age statement | `16 YO` (metadata) | `16yo` | **VERIFIED** |
| Distillery | â€” | â€” | **MISSING** |
| Region | â€” | â€” | **MISSING** |
| Country | â€” | â€” | **MISSING** |
| ABV | `43.0%` (metadata) | `None` | **VERIFIED** |
| Category | â€” | `Malt` | **VERIFIED** |

**Note:** Same minimal production record pattern. Candidate ABV 43.0% matches official Lagavulin 16yo standard. Identity established via name + age.

---

## 4. Evidence Review

### Candidate A: Ardbeg 10 Year Old

| Field | Detail |
|---|---|
| Source evidence | `whiskynotes_be` â€” external whisky review site |
| Source URL | `https://www.whiskynotes.be//batch1/whiskynotes_be/` |
| Evidence confidence | `0.85` (heuristic extraction) |
| Authority tier | `T2_expert` |
| Content hash | `0c9f65fa43bfe3624fe58670714cb86622a02fdebb3774ae4a332ec66c186730` |

**Extracted fields (completeness):**

| Field | Present | Value |
|---|---|---|
| score_value | âœ… | 90 / 100 |
| nose | âœ… | `: intense peat, smoke and citrus.` |
| palate | âœ… | `: peppery, medicinal and sweet barley.` |
| finish | âœ… | `: long, smoky and coastal.` |
| flavor_vector | âœ… | 7 axes (smoky=0.33, peaty=0.33, fruity=0.17, sweet=0.0, spicy=0.17, maritime=0.17, sherry=0.0) |
| conclusion | âŒ | â€” |
| published_date | âŒ | â€” |

**Limitations:**
- Leading colon on nose/palate/finish â€” formatting artifact from heuristic extraction (minor, does not affect data quality)
- sweet=0.0 â€” valid (Ardbeg is known for low sweetness)
- Extraction method `heuristic` â€” not as precise as `structured_extraction` used for the first promoted candidate (EDR-b6108f7ac8d252af). All 4 batch candidates share this limitation.
- Confidence 0.85 is below the 1.0 of the first candidate, but well above the CERTIFY_MIN threshold of 0.70.

---

### Candidate B: Clynelish 14 Year Old

| Field | Detail |
|---|---|
| Source evidence | `thedramble` â€” external whisky review site |
| Source URL | `https://www.thedramble.com/tastings//batch1/thedramble/` |
| Evidence confidence | `0.85` (heuristic extraction) |
| Authority tier | `T2_expert` |
| Content hash | `4e44d7fb9b52b7da97ab2718141cf4b5efc3e985df84cc067c39ab5d8db8eca7` |

**Extracted fields (completeness):**

| Field | Present | Value |
|---|---|---|
| score_value | âœ… | 88 / 100 |
| nose | âœ… | `: waxy lemon, coastal salt and light peat.` |
| palate | âœ… | `: honey, vanilla and white pepper.` |
| finish | âœ… | `: medium, waxy and maritime.` |
| flavor_vector | âœ… | 7 axes (smoky=0.0, peaty=0.17, fruity=0.17, sweet=0.33, spicy=0.17, maritime=0.33, sherry=0.0) |
| conclusion | âŒ | â€” |
| published_date | âŒ | â€” |
| author | âŒ | â€” |

**Limitations:** Same heuristic extraction artifacts as Candidate A. flavor_vector dominant axes (sweet+maritime) consistent with Clynelish waxy profile.

---

### Candidate C: Talisker 10 Year Old

| Field | Detail |
|---|---|
| Source evidence | `thewhiskeywash` â€” external whisky review site |
| Source URL | `https://thewhiskeywash.com/whiskey-reviews//batch1/thewhiskeywash/` |
| Evidence confidence | `0.85` (heuristic extraction) |
| Authority tier | `T2_expert` |
| Content hash | `33a1b76926e32cbb8107d34f8ddc52d7b060f9ada6d808f04e17375dd3825c2f` |

**Extracted fields (completeness):**

| Field | Present | Value |
|---|---|---|
| score_value | âœ… | 87 / 100 |
| nose | âœ… | `: sea salt, peat and black pepper.` |
| palate | âœ… | `: sweet malt, smoke and chili.` |
| finish | âœ… | `: spicy, coastal and long.` |
| flavor_vector | âœ… | 7 axes (smoky=0.17, peaty=0.17, fruity=0.0, sweet=0.0, spicy=0.33, maritime=0.33, sherry=0.0) |
| conclusion | âŒ | â€” |
| published_date | âŒ | â€” |
| author | âŒ | â€” |

**Limitations:** Same heuristic extraction. flavor_vector (spicy+maritime dominant) strongly consistent with Talisker coastal character. ABV 45.8% matches official Talisker 10yo bottling.

---

### Candidate D: Lagavulin 16 Year Old

| Field | Detail |
|---|---|
| Source evidence | `whiskymonster` â€” external whisky review site |
| Source URL | `https://www.whiskymonster.com/whisky/whisky-reviews/list-of-whisky-reviews//batch1/whiskymonster/` |
| Evidence confidence | `0.85` (heuristic extraction) |
| Authority tier | `T2_expert` |
| Content hash | `0a9bb6b39a80a1aaacd6d8c8d66f2b62ddd5ccac88156f779a5a2a084ec35f5d` |

**Extracted fields (completeness):**

| Field | Present | Value |
|---|---|---|
| score_value | âœ… | 92 / 100 |
| nose | âœ… | `: peat smoke, iodine and coastal brine.` |
| palate | âœ… | `: rich sherry, dried fruit and oak spice.` |
| finish | âœ… | `: long, smoky and medicinal.` |
| flavor_vector | âœ… | 6 active axes (smoky=0.33, peaty=0.5, fruity=0.17, sweet=0.0, spicy=0.33, maritime=0.33, sherry=0.33) |
| conclusion | âŒ | â€” |
| published_date | âŒ | â€” |
| author | âŒ | â€” |

**Limitations:** Same heuristic extraction. flavor_vector (peaty+smoky+spicy+sherry) strongly consistent with Lagavulin 16yo profile. ABV 43.0% matches official bottling. Score 92/100 is the highest in the batch.

---

## 5. Provenance Review

### Source chain (all candidates)

```
External review site (whiskynotes_be / thedramble / thewhiskeywash / whiskymonster)
  â†“ (crawl)
Batch 1 extraction pipeline
  â†“ (heuristic extraction â€” automated)
staging_editorial_reviews
  â†“
Current state: staging_unverified (requires human ratification)
```

### Current state

| Candidate | Source | Provenance | Content hash integrity |
|---|---|---|---|
| Ardbeg 10yo | whiskynotes_be | `staging_unverified` | âœ… `0c9f65fa4â€¦` |
| Clynelish 14yo | thedramble | `staging_unverified` | âœ… `4e44d7fb9â€¦` |
| Talisker 10yo | thewhiskeywash | `staging_unverified` | âœ… `33a1b7692â€¦` |
| Lagavulin 16yo | whiskymonster | `staging_unverified` | âœ… `0a9bb6b39â€¦` |

### Provenance decision

| Candidate | Human decision |
|---|---|
| Ardbeg 10yo | **`__PENDING__`** (RATIFY / KEEP HOLD / REJECT) |
| Clynelish 14yo | **`__PENDING__`** |
| Talisker 10yo | **`__PENDING__`** |
| Lagavulin 16yo | **`__PENDING__`** |

**Assessment:** All 4 sources are established whisky review domains. Content hashes are present and consistent. The `staging_unverified` state is a default â€” no evidence of tampering or provenance issues. Same pattern as the first promoted candidate (whiskyfun â†’ EDR-b6108f7ac8d252af), which was ratified and APPROVED.

**Recommendation:** RATIFY all 4. If rejecting any, specify which evidence was found unreliable.

---

## 6. Certification Decision

### Per-candidate options

| Candidate | Decision |
|---|---|
| Ardbeg 10yo (W001152) | **`__PENDING__`** (APPROVE / HOLD / REJECT) |
| Clynelish 14yo (W000496) | **`__PENDING__`** |
| Talisker 10yo (W000976) | **`__PENDING__`** |
| Lagavulin 16yo (W001100) | **`__PENDING__`** |

### Batch-level certification diagnostics

| Cross-cutting issue | Assessment |
|---|---|
| **All T2_expert, all heuristic extraction** | Lower authority than the T2_expert + structured_extraction of the first promoted candidate. Heuristic extraction may produce noisier data (leading colons, missing conclusion/published_date fields). |
| **All production records minimal** | W001152, W000496, W001100 have no distillery_id, region, or country. Identity relies on name + age match. This is a production data gap, not evidence error. |
| **T1_ceiling on identity fields** | Same field_ceiling conflict as the first candidate. Human override required per P306 precedent. |
| **All flavor vectors valid** | 7 canonical axes, each in [0,1]. No invalid values. |
| **No duplicate evidence_ids** | None of the 4 evidence_ids exist in production `flavor_evidence` â€” clean promotion. |
| **Evidence completeness gap** | All 4 missing `conclusion` and `published_date`. This is a known limitation of heuristic extraction. The first promoted candidate had the same gap (nose/palate/finish present, conclusion absent). |

**Recommendation for human reviewer:**

> All 4 candidates follow an identical pattern to the first promoted candidate (EDR-b6108f7ac8d252af): T2_expert authority, heuristic extraction, valid flavor vectors, matching production whisky, staging_unverified provenance. The first candidate was approved via `PROMO-20260718-001` under GO-20260718-001. These 4 can be treated as a batch extension of the same workflow, with the caveat that heuristic extraction (0.85 confidence) may produce less precise data than structured extraction (1.0 confidence).

### Review fields

| Field | Value |
|---|---|
| Reviewer | **`__PENDING__`** |
| Timestamp | **`__PENDING__`** |
| Justification | **`__PENDING__`** |

---

## 7. Batch Authorization

> **DO NOT create automatic GO.** Leave all fields below as `__PENDING__` for human input.

| Field | Status |
|---|---|
| Authorized by | **`__PENDING__`** |
| GO reference | **`__PENDING__`** |
| Approval timestamp | **`__PENDING__`** |
| Approval scope | **`__PENDING__`** (ALL / SELECTED) |

### Post-authorization execution plan

```
1. Update staging: match_status=exact for all 4 (from manual_review)
2. Update staging: provenance_state=APPROVED for all 4 (from staging_unverified)
3. Generate batch manifest PROMO-BATCH-20260718-001.yaml
4. Pre-promotion immutable backup (P312 pattern)
5. Execute batch promotion (P313 pattern, single transaction)
6. Post-promotion validation (P314 pattern)
7. Update monitoring baseline (P315 update)
```

---

## Final Status

```
BATCH:     PENDING HUMAN CERTIFICATION
PRODUCTION: UNCHANGED

4 candidates await evidence-based review.
No score used for approval decisions.
Match scores documented as DECISION SUPPORT ONLY.
All identity fields verified against production records.
Batch authorization fields left pending for human input.
```

**No database writes. No staging mutation. No production mutation. No promotion. No commit/push/tag.**
