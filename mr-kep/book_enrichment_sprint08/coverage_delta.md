# Coverage Delta — Sprint 08 (Dave Broom Whisky: The Manual, DB_MANUAL)

**Source:** Whisky: The Manual (Dave Broom, 2014)
**Source ID:** `DB_MANUAL`  |  **Run:** `RUN_ENRICHMENT_DBM_20260715_162033`
**Timestamp:** 2026-07-15T16:23:22.747943Z

---

## Knowledge.db Delta (Sprint 08 only)

| Table | Pre (after S07) | Post (after S08) | Delta |
|-------|:-:|:-:|:-:|
| books | 23 | 24 | **+1** |
| book_versions | 23 | 24 | **+1** |
| citations | 12689 | 13133 | **+444** |
| evidence_nodes | 12689 | 13133 | **+444** |
| extracted_facts | 12689 | 13133 | **+444** |
| consensus_nodes | 2951 | 3077 | **+126** |
| canonical_vectors | 2951 | 3077 | **+126** |
| promotion_candidates | 3071 | 3101 | **+30** |

### New whisky_ids covered this sprint
**+1** (distinct whisky_ids with consensus)

---

## Cumulative Coverage Dashboard (S01-S08)

| Metric | Prior (S01-S07) | Sprint 08 | Cumulative |
|--------|:-:|:-:|:-:|
| Books/sources | 6 | 1 (DB_MANUAL, EPUB) | **7** |
| whisky_ids covered | 1736 | +1 | **1737** |
| Citations | 12689 | +444 | **13133** |
| Evidence nodes | 12689 | +444 | **13133** |
| Extracted facts | 12689 | +444 | **13133** |
| Canonical vectors | 2951 | +126 | **3077** |

### Coverage Percentage
- **Universe:** 3557 whiskies in production.db
- **Covered:** 1737
- **Coverage:** 48.83%

---

## Manual Review Backlog
- **Unresolved entities (S08):** 71
- **Total manual review queue:** 71 (see `manual_review_queue.csv`)

---

## Validation
- PRAGMA integrity_check == ok OK
- PRAGMA foreign_key_check == 0
- Zero orphan rows (evidence 0, facts 0)
- Fact:evidence 1:1 (facts 444 == evidence 444)
- Schema signature unchanged (52128031e1cdaef60db7988a24dc7bf77033d66a146560607c37d95ad721526c == 52128031e1cdaef60db7988a24dc7bf77033d66a146560607c37d95ad721526c)
- Previous consensus NOT overwritten (unique per (whisky_id, algorithm_version))
- production.db untouched
- Status='ACTIVE' on new records
- NO INSERT OR IGNORE used (crash+rollback on violation)
