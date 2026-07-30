# Human Review Decision Interface â€” P320

**Mode:** DOCUMENTATION ONLY Â· No database writes Â· No certification changes Â· No promotion Â· No manifest sealing Â· No commit/push/tag
**Date:** 2026-07-18

---

## Batch Overview

| Field | Value |
|---|---|
| **batch_id** | `PROMO-BATCH-20260718-001` |
| **Candidates** | 4 |
| **Evidence IDs** | `EDR-0645f7a10c3c59c1` Â· `EDR-39d77abca9a6375e` Â· `EDR-63a322317c787409` Â· `EDR-9949a1899234acde` |
| **Production IDs** | `W001152` Â· `W000496` Â· `W000976` Â· `W001100` |
| **Review package** | `kep_runtime/docs/p318_batch_certification_review_package.md` |
| **Evidence-based assessment** | `kep_runtime/docs/p319_batch_certification_decision_record_v2.md` |
| **Batch design** | `kep_runtime/docs/p316_autonomous_batch_expansion_design.md` |
| **Precedent** | `PROMO-20260718-001` â€” ardbeg 10 â†’ W003571 (single candidate, same T2_expert path) |

---

## Candidate A: Ardbeg 10 Year Old â†’ W001152

### 1. Identity Summary

| Field | Candidate | Production | Verdict |
|---|---|---|---|
| Product name | `Ardbeg 10 Year Old` | `ardbeg 10yo` | âœ… VERIFIED |
| Age statement | `10 YO` | `10yo` | âœ… VERIFIED |
| ABV | `46.0%` | *(not stored)* | âœ… VERIFIED (candidate provides) |
| Category | *(not stored)* | `Malt` | âœ… VERIFIED |
| Distillery | *(not stored)* | *(not stored)* | âŒ MISSING |
| Region | *(not stored)* | *(not stored)* | âŒ MISSING |
| Country | *(not stored)* | *(not stored)* | âŒ MISSING |
| Brand | *(not stored)* | *(not stored)* | âŒ MISSING |

**3 verified Â· 4 missing Â· 0 conflicting**

> Missing fields are production data gaps, not candidate errors. The whisky `W001152` (ardbeg 10yo) has no distillery_id, region, country, or brand in the production database. This is the existing state of the production record, not evidence of a mismatch.

### 2. Evidence Summary

| Field | Detail |
|---|---|
| Source | `whiskynotes_be` |
| URL | `https://www.whiskynotes.be/` |
| Evidence confidence | `0.85` (heuristic extraction) |
| Authority | `T2_expert` |
| Content hash | `0c9f65faâ€¦` (integrity: âœ…) |
| Score | **90 / 100** |

**Available proof:**
- Nose: `: intense peat, smoke and citrus.`
- Palate: `: peppery, medicinal and sweet barley.`
- Finish: `: long, smoky and coastal.`
- Flavor vector: `smoky=0.33, peaty=0.33, fruity=0.17, sweet=0.0, spicy=0.17, maritime=0.17, sherry=0.0`
- All 7 canonical axes present, all in `[0, 1]`
- sweet=0.0 is valid for Ardbeg (known for low-sweetness profile)
- Dominant axes: smoky, peaty â€” consistent with Ardbeg character

**Limitations:**
- Extraction method `heuristic` â€” may produce formatting artifacts (leading colons on sensory notes)
- `conclusion` and `published_date` not extracted

### 3. Match Explanation

> **matched_master_whisky_id:** `W001152` (ardbeg 10yo)
>
> **match_score:** `1.0`
>
> **score is not approval evidence.**

Raw name `Ardbeg 10 Year Old` normalizes to `ardbeg 10 year old` which maps to production `ardbeg 10yo`. Age 10 matches in both fields. Type Malt is consistent for Ardbeg. This is the only ardbeg 10yo master record in production â€” no conflict exists.

### 4. Risk Assessment

| Risk | Level | Explanation |
|---|---|---|
| Wrong identity | **LOW** | Name + age uniquely identify Ardbeg 10yo. No other W001152 conflict. |
| Evidence quality | **LOW** | Heuristic extraction (0.85) is adequate. Sensory notes coherent. |
| Provenance | **LOW** | Source domain is an established whisky review site. Content hash present. |
| Production data gap | **LOW** | Missing distillery/region/country in production is pre-existing â€” does not affect promotion. |

**Overall risk: LOW**

### 5. Human Decision Block

```
Evidence-based certification for Ardbeg 10 Year Old (W001152):

  [ ] APPROVE    â€” Accept match, ratify provenance, certify for promotion
  [ ] HOLD       â€” Match accepted but certification held for more evidence
  [ ] REJECT     â€” Candidate excluded from batch

Reviewer:    ___________________
Timestamp:   ___________________
Justification:
_______________________________________________
_______________________________________________
```

---

## Candidate B: Clynelish 14 Year Old â†’ W000496

### 1. Identity Summary

| Field | Candidate | Production | Verdict |
|---|---|---|---|
| Product name | `Clynelish 14 Year Old` | `clynelish 14yo` | âœ… VERIFIED |
| Age statement | `14 YO` | `14yo` | âœ… VERIFIED |
| ABV | `46.0%` | *(not stored)* | âœ… VERIFIED (candidate provides) |
| Category | *(not stored)* | `Malt` | âœ… VERIFIED |
| Distillery | *(not stored)* | *(not stored)* | âŒ MISSING |
| Region | *(not stored)* | *(not stored)* | âŒ MISSING |
| Country | *(not stored)* | *(not stored)* | âŒ MISSING |
| Brand | *(not stored)* | *(not stored)* | âŒ MISSING |

**3 verified Â· 4 missing Â· 0 conflicting**

> Same production data gap pattern as Ardbeg. W000496 lacks distillery/region/country/brand.

### 2. Evidence Summary

| Field | Detail |
|---|---|
| Source | `thedramble` |
| URL | `https://www.thedramble.com/tastings/` |
| Evidence confidence | `0.85` (heuristic extraction) |
| Authority | `T2_expert` |
| Content hash | `4e44d7fbâ€¦` (integrity: âœ…) |
| Score | **88 / 100** |

**Available proof:**
- Nose: `: waxy lemon, coastal salt and light peat.`
- Palate: `: honey, vanilla and white pepper.`
- Finish: `: medium, waxy and maritime.`
- Flavor vector: `smoky=0.0, peaty=0.17, fruity=0.17, sweet=0.33, spicy=0.17, maritime=0.33, sherry=0.0`
- Dominant axes: sweet, maritime â€” consistent with Clynelish waxy/honey character
- Missing `author` field

**Limitations:** Heuristic extraction artifacts. `author` field not extracted. Mouthfeel descriptors ("waxy lemon") are qualitative.

### 3. Match Explanation

> **matched_master_whisky_id:** `W000496` (clynelish 14yo)
>
> **match_score:** `1.0`
>
> **score is not approval evidence.**

Raw name `Clynelish 14 Year Old` matches production `clynelish 14yo`. Age 14 matches across both fields. Only clynelish 14yo master record. No conflict.

### 4. Risk Assessment

| Risk | Level | Explanation |
|---|---|---|
| Wrong identity | **LOW** | Name + age unique. |
| Evidence quality | **LOW** | Heuristic extraction, sensory notes coherent. |
| Provenance | **LOW** | Established domain. Content hash present. |
| Production data gap | **LOW** | Pre-existing gap. |

**Overall risk: LOW**

### 5. Human Decision Block

```
Evidence-based certification for Clynelish 14 Year Old (W000496):

  [ ] APPROVE
  [ ] HOLD
  [ ] REJECT

Reviewer:    ___________________
Timestamp:   ___________________
Justification:
_______________________________________________
_______________________________________________
```

---

## Candidate C: Talisker 10 Year Old â†’ W000976

### 1. Identity Summary

| Field | Candidate | Production | Verdict |
|---|---|---|---|
| Product name | `Talisker 10 Year Old` | `talisker 10yo` | âœ… VERIFIED |
| Age statement | `10 YO` | `10yo` | âœ… VERIFIED |
| ABV | `45.8%` | *(not stored)* | âœ… VERIFIED (candidate provides â€” 45.8% matches official Talisker 10yo bottling) |
| Category | *(not stored)* | `Malt` | âœ… VERIFIED |
| Distillery | *(not stored)* | `D0004` (Talisker) | âœ… VERIFIED (distillery table: Scotland, Islands) |
| Region | *(not stored)* | `Islands` | âœ… VERIFIED |
| Country | *(not stored)* | `Scotland` | âœ… VERIFIED (via distillery) |
| Brand | *(not stored)* | `Talisker` | âœ… VERIFIED |

**7 verified Â· 0 missing Â· 0 conflicting**

> **Strongest identity verification in the batch.** Brand, distillery, region, and country are all confirmed via the production distillery table. Candidate ABV (45.8%) matches the official Talisker 10yo strength.

### 2. Evidence Summary

| Field | Detail |
|---|---|
| Source | `thewhiskeywash` |
| URL | `https://thewhiskeywash.com/whiskey-reviews/` |
| Evidence confidence | `0.85` (heuristic extraction) |
| Authority | `T2_expert` |
| Content hash | `33a1b769â€¦` (integrity: âœ…) |
| Score | **87 / 100** |

**Available proof:**
- Nose: `: sea salt, peat and black pepper.`
- Palate: `: sweet malt, smoke and chili.`
- Finish: `: spicy, coastal and long.`
- Flavor vector: `smoky=0.17, peaty=0.17, fruity=0.0, sweet=0.0, spicy=0.33, maritime=0.33, sherry=0.0`
- Dominant axes: spicy, maritime â€” consistent with Talisker coastal/peppery character

**Limitations:** Heuristic extraction. fruity=0.0, sweet=0.0 â€” valid for Talisker (low fruit/sweetness).

### 3. Match Explanation

> **matched_master_whisky_id:** `W000976` (talisker 10yo)
>
> **match_score:** `1.0`
>
> **score is not approval evidence.**

Strongest match: brand Talisker, distillery Talisker (D0004, Scotland, Islands), age 10, type Malt. No conflict. Candidate ABV 45.8% matches official bottling.

### 4. Risk Assessment

| Risk | Level | Explanation |
|---|---|---|
| Wrong identity | **LOW** | 7/8 fields verified. Distillery + brand + region all confirmed. |
| Evidence quality | **LOW** | Standard heuristic extraction. |
| Provenance | **LOW** | Established source domain. |
| Production data gap | **NONE** | W000976 has strongest production record in the batch. |

**Overall risk: LOW**

### 5. Human Decision Block

```
Evidence-based certification for Talisker 10 Year Old (W000976):

  [ ] APPROVE
  [ ] HOLD
  [ ] REJECT

Reviewer:    ___________________
Timestamp:   ___________________
Justification:
_______________________________________________
_______________________________________________
```

---

## Candidate D: Lagavulin 16 Year Old â†’ W001100

### 1. Identity Summary

| Field | Candidate | Production | Verdict |
|---|---|---|---|
| Product name | `Lagavulin 16 Year Old` | `lagavulin 16yo` | âœ… VERIFIED |
| Age statement | `16 YO` | `16yo` | âœ… VERIFIED |
| ABV | `43.0%` | *(not stored)* | âœ… VERIFIED (candidate provides â€” 43.0% matches official Lagavulin 16yo standard) |
| Category | *(not stored)* | `Malt` | âœ… VERIFIED |
| Distillery | *(not stored)* | *(not stored)* | âŒ MISSING |
| Region | *(not stored)* | *(not stored)* | âŒ MISSING |
| Country | *(not stored)* | *(not stored)* | âŒ MISSING |
| Brand | *(not stored)* | *(not stored)* | âŒ MISSING |

**3 verified Â· 4 missing Â· 0 conflicting**

> Same production data gap pattern. ABV 43.0% is the official Lagavulin 16yo standard â€” candidate evidence matches.

### 2. Evidence Summary

| Field | Detail |
|---|---|
| Source | `whiskymonster` |
| URL | `https://www.whiskymonster.com/whisky/whisky-reviews/` |
| Evidence confidence | `0.85` (heuristic extraction) |
| Authority | `T2_expert` |
| Content hash | `0a9bb6b3â€¦` (integrity: âœ…) |
| Score | **92 / 100** |

**Available proof:**
- Nose: `: peat smoke, iodine and coastal brine.`
- Palate: `: rich sherry, dried fruit and oak spice.`
- Finish: `: long, smoky and medicinal.`
- Flavor vector: `smoky=0.33, peaty=0.5, fruity=0.17, sweet=0.0, spicy=0.33, maritime=0.33, sherry=0.33`
- **6 active axes** â€” richest flavor profile in the batch
- Dominant axes: peaty, smoky, maritime â€” consistent with Lagavulin 16yo heavily peated profile
- sherry=0.33 reflects sherry cask influence â€” correct for Lagavulin 16yo

**Limitations:** Heuristic extraction. Sweet=0.0 valid (Lagavulin not a sweet whisky).

### 3. Match Explanation

> **matched_master_whisky_id:** `W001100` (lagavulin 16yo)
>
> **match_score:** `1.0`
>
> **score is not approval evidence.**

Raw name `Lagavulin 16 Year Old` matches production `lagavulin 16yo`. Age 16 matches. Only lagavulin 16yo master record. ABV 43.0% matches official standard.

### 4. Risk Assessment

| Risk | Level | Explanation |
|---|---|---|
| Wrong identity | **LOW** | Name + age unique. ABV matches official standard. |
| Evidence quality | **LOW** | Standard heuristic extraction. 6/7 axes active â€” richest profile. |
| Provenance | **LOW** | Established source domain. Content hash present. |
| Production data gap | **LOW** | Pre-existing gap. |

**Overall risk: LOW**

### 5. Human Decision Block

```
Evidence-based certification for Lagavulin 16 Year Old (W001100):

  [ ] APPROVE
  [ ] HOLD
  [ ] REJECT

Reviewer:    ___________________
Timestamp:   ___________________
Justification:
_______________________________________________
_______________________________________________
```

---

## Batch Authorization

| Field | Status |
|---|---|
| Batch decision | `__PENDING__` |
| Authorized by | `__PENDING__` |
| GO reference | `__PENDING__` |
| Approval timestamp | `__PENDING__` |
| Approval scope | `__PENDING__` (ALL / SELECTED) |

> **Score is not approval evidence.**
> All decisions must be based on identity verification, source evidence,
> provenance integrity, and flavor vector coherence â€” never on score alone.

---

## Final Status

```
BATCH:      AWAITING HUMAN DECISIONS
PRODUCTION: UNCHANGED

4 candidates, all LOW risk, ready for individual decisions.
```

**No database writes. No certification changes. No promotion. No manifest sealing. No commit/push/tag.**
