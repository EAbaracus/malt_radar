# Coverage Delta — Sprint 02 (World Atlas of Whisky)

**Book:** The World Atlas of Whisky — Dave Broom (ISBN: 9781845335588)
**Priority:** B2 / P0 (next highest after Sprint 01's B1)
**Book Key:** `WAW2011_B2`
**Timestamp:** 2026-07-15T11:46:16.503159Z

---

## Knowledge.db Delta (Sprint 02 only)

| Table | Pre (after S01) | Post (after S02) | Delta |
|-------|:-:|:-:|:-:|
| books | 19 | 20 | **+1** |
| book_versions | 19 | 20 | **+1** |
| citations | 2624 | 4669 | **+2045** |
| evidence_nodes | 2624 | 4669 | **+2045** |
| extracted_facts | 2624 | 4669 | **+2045** |
| consensus_nodes | 583 | 893 | **+310** |
| canonical_vectors | 583 | 893 | **+310** |
| promotion_candidates | 607 | 917 | **+310** |

### New whisky_ids covered this sprint
**+264** (distinct whisky_ids with consensus)

---

## Cumulative Coverage Dashboard (S01 + S02)

| Metric | Sprint 01 | Sprint 02 | Cumulative |
|--------|:-:|:-:|:-:|
| Books processed | 1 (B1) | 1 (B2) | **2** |
| whisky_ids covered | 476 | +264 | **740** |
| Citations | 2,624 | +2045 | **4669** |
| Evidence nodes | 2,624 | +2045 | **4669** |
| Extracted facts | 2,624 | +2045 | **4669** |
| Canonical vectors | 583 | +310 | **893** |

### Coverage Percentage
- **Universe:** 3557 whiskies in production.db
- **Covered:** 740
- **Coverage:** 20.8%

---

## Manual Review Backlog
- **Unresolved entities (S02):** 256
- **Total manual review queue:** 256 (see `manual_review_queue.csv`)

---

## Validation
- PRAGMA integrity_check == OK ✅
- PRAGMA foreign_key_check == 0 ✅
- Zero orphan rows ✅
- Fact:evidence 1:1 ✅
- Deterministic hashes ✅
- Schema signature unchanged ✅
- production.db remains untouched ✅
