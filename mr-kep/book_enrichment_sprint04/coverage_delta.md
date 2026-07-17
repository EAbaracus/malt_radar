# Coverage Delta — Sprint 04 (Whisky Advocate Archive, WA_ARCH)

**Source:** Whisky Advocate Archive (2020-2026)
**Issues:** 14 Whisky Advocate PDFs (2020-2026)
**Source ID:** `WA_ARCH`  |  **Run:** `RUN_ENRICHMENT_WA_20260715_124154`
**Timestamp:** 2026-07-15T12:50:16.269773Z

---

## Knowledge.db Delta (Sprint 04 only)

| Table | Pre (after S03) | Post (after S04) | Delta |
|-------|:-:|:-:|:-:|
| books | 21 | 22 | **+1** |
| book_versions | 21 | 22 | **+1** |
| citations | 5436 | 10138 | **+4702** |
| evidence_nodes | 5436 | 10138 | **+4702** |
| extracted_facts | 5436 | 10138 | **+4702** |
| consensus_nodes | 1057 | 2239 | **+1182** |
| canonical_vectors | 1057 | 2239 | **+1182** |
| promotion_candidates | 1456 | 2263 | **+807** |

### New whisky_ids covered this sprint
**+773** (distinct whisky_ids with consensus)

---

## Cumulative Coverage Dashboard (S01-S04)

| Metric | Prior (S01-S03) | Sprint 04 | Cumulative |
|--------|:-:|:-:|:-:|
| Books processed | 3 | 14 (WA_ARCH) | **17** |
| whisky_ids covered | 771 | +773 | **1544** |
| Citations | 5,436 | +4702 | **10138** |
| Evidence nodes | 5,436 | +4702 | **10138** |
| Extracted facts | 5,436 | +4702 | **10138** |
| Canonical vectors | 1,057 | +1182 | **2239** |

### Coverage Percentage
- **Universe:** 3557 whiskies in production.db
- **Covered:** 1544
- **Coverage:** 43.41%

---

## Manual Review Backlog
- **Unresolved entities (S04):** 336
- **Total manual review queue:** 336 (see `manual_review_queue.csv`)

---

## Validation
- PRAGMA integrity_check == ok ✅
- PRAGMA foreign_key_check == 0 ✅
- Zero orphan rows (evidence 0, facts 0) ✅
- Fact:evidence 1:1 (facts 4702 == evidence 4702) ✅
- Schema signature unchanged ✅
- production.db untouched ✅
- Status='ACTIVE' on new records ✅
- NO INSERT OR IGNORE used (crash+rollback on violation) ✅
