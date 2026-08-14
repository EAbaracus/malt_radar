# Coverage Delta — Sprint 07 (Jim Murray's Whisky Bible 2020, JMB2020)

**Source:** Jim Murray's Whisky Bible 2020 (Rest of the World)
**Source ID:** `JMB2020`  |  **Run:** `RUN_ENRICHMENT_JMB_20260715_154035`
**Timestamp:** 2026-07-15T15:40:36.735379Z

---

## Knowledge.db Delta (Sprint 07 only)

| Table | Pre (after S06) | Post (after S07) | Delta |
|-------|:-:|:-:|:-:|
| books | 22 | 23 | **+1** |
| book_versions | 22 | 23 | **+1** |
| citations | 10138 | 12689 | **+2551** |
| evidence_nodes | 10138 | 12689 | **+2551** |
| extracted_facts | 10138 | 12689 | **+2551** |
| consensus_nodes | 2239 | 2951 | **+712** |
| canonical_vectors | 2239 | 2951 | **+712** |
| promotion_candidates | 2263 | 2975 | **+712** |

### New whisky_ids covered this sprint
**+192** (distinct whisky_ids with consensus)

---

## Cumulative Coverage Dashboard (S01-S07)

| Metric | Prior (S01-S06) | Sprint 07 | Cumulative |
|--------|:-:|:-:|:-:|
| Books/sources | 5 | 1 (JMB2020) | **6** |
| whisky_ids covered | 1544 | +192 | **1736** |
| Citations | 10138 | +2551 | **12689** |
| Evidence nodes | 10138 | +2551 | **12689** |
| Extracted facts | 10138 | +2551 | **12689** |
| Canonical vectors | 2239 | +712 | **2951** |

### Coverage Percentage
- **Universe:** 3557 whiskies in production.db
- **Covered:** 1736
- **Coverage:** 48.81%

---

## Manual Review Backlog
- **Unresolved entities (S07):** 338
- **Total manual review queue:** 338 (see `manual_review_queue.csv`)

---

## Validation
- PRAGMA integrity_check == ok OK
- PRAGMA foreign_key_check == 0
- Zero orphan rows (evidence 0, facts 0)
- Fact:evidence 1:1 (facts 2551 == evidence 2551)
- Schema signature unchanged (52128031e1cdaef60db7988a24dc7bf77033d66a146560607c37d95ad721526c == 52128031e1cdaef60db7988a24dc7bf77033d66a146560607c37d95ad721526c)
- production.db untouched
- Status='ACTIVE' on new records
- NO INSERT OR IGNORE used (crash+rollback on violation)
