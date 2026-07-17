# Coverage Delta — Sprint 03 (Michael Jackson: The World Guide to Whisky)

**Book:** The World Guide to Whisky — Michael Jackson (ISBN: 9780881622843)
**Matrix Ref:** B3 / P1 / GO (historical enrichment)
**Book Key:** `MJ1987_B3`  |  **Run:** `RUN_ENRICHMENT_B3_20260715_122208`
**Timestamp:** 2026-07-15T12:22:08.490507Z

---

## Knowledge.db Delta (Sprint 03 only)

| Table | Pre (after S02) | Post (after S03) | Delta |
|-------|:-:|:-:|:-:|
| books | 20 | 21 | **+1** |
| book_versions | 20 | 21 | **+1** |
| citations | 4669 | 5436 | **+767** |
| evidence_nodes | 4669 | 5436 | **+767** |
| extracted_facts | 4669 | 5436 | **+767** |
| consensus_nodes | 893 | 1057 | **+164** |
| canonical_vectors | 893 | 1057 | **+164** |
| promotion_candidates | 917 | 1081 | **+164** |

### New whisky_ids covered this sprint
**+31** (distinct whisky_ids with consensus)

---

## Cumulative Coverage Dashboard (S01 + S02 + S03)

| Metric | Prior (S01+S02) | Sprint 03 | Cumulative |
|--------|:-:|:-:|:-:|
| Books processed | 2 | 1 (B3) | **3** |
| whisky_ids covered | 740 | +31 | **771** |
| Citations | 4,669 | +767 | **5436** |
| Evidence nodes | 4,669 | +767 | **5436** |
| Extracted facts | 4,669 | +767 | **5436** |
| Canonical vectors | 893 | +164 | **1057** |

### Coverage Percentage
- **Universe:** 3557 whiskies in production.db
- **Covered:** 771
- **Coverage:** 21.68%

---

## Manual Review Backlog
- **Unresolved entities (S03):** 146
- **Total manual review queue:** 146 (see `manual_review_queue.csv`)

---

## Validation
- PRAGMA integrity_check == ok ✅
- PRAGMA foreign_key_check == 0 ✅
- Zero orphan rows (evidence 0, facts 0) ✅
- Fact:evidence 1:1 (facts 767 == evidence 767) ✅
- Schema signature unchanged ✅
- production.db untouched ✅
- Status='ACTIVE' on new records ✅
- NO INSERT OR IGNORE used (crash+rollback on violation) ✅
