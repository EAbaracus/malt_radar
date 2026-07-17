# Book Enrichment Sprint 02 — Report

**Book:** The World Atlas of Whisky
**Author:** Dave Broom
**ISBN:** 9781845335588
**Publisher:** Octopus Publishing Group
**Source Priority:** B2 / P0 (next highest priority after Sprint 01's B1)
**Book Key (source-scoped, collision-free):** `WAW2011_B2`
**Timestamp:** 2026-07-15T11:46:16.503159Z

---

## 1. Source Selection

Sprint 01 processed **B1 (Malt Whisky Yearbook 2019, P0/GO)** — the highest-priority
approved source. Per the frozen `source_priority_matrix.md`, the next highest-priority
approved book source is **B2 (World Atlas of Whisky, Dave Broom, P0/GO)**.

The frozen Sprint 01 enrichment extractor/resolver/consensus functions were reused
**unchanged**. A source-scoped, collision-free DB loader was used (see §8 note) because
the raw filename hash `a10b6a6cc9bc` collides with a pre-existing mock book identity
from the original P103 ingestion.

---

## 2. Inventory

- **Total Pages:** 171 (all text-extractable: 171/171)
- **Total Characters:** 1,116,617
- **Lexicon (production.db):** 13,330 entries
- **Source Class:** Book — T3_community

---

## 3. Extraction & Resolution

| Metric | Value |
|--------|-------|
| Total entities matched | 751 |
| Resolved to whisky_id | 495 |
| Unresolved (distillery/partial) | 256 |
| Resolution rate | 65.91% |

---

## 4. Knowledge.db Delta

| Table | Delta |
|-------|:-----:|
| books | +1 |
| book_versions | +1 |
| citations | +2045 |
| evidence_nodes | +2045 |
| extracted_facts | +2045 |
| consensus_nodes | +310 |
| canonical_vectors | +310 |
| promotion_candidates | +310 |
| **New whisky_ids covered** | **+264** |

---

## 5. Coverage Dashboard (Cumulative S01+S02)

- **Total whisky coverage:** 740 distinct whisky_ids
- **Newly covered this sprint:** 264
- **New citations:** 2045
- **New evidence_nodes:** 2045
- **New extracted_facts:** 2045
- **New canonical_vectors:** 310
- **Source contribution (B2):** The World Atlas of Whisky → 310 vectors
- **Coverage percentage:** 20.8% of 3557 universe
- **Manual review backlog:** 256 unresolved entities

---

## 6. Validation Results

| Check | Result |
|-------|--------|
| PRAGMA integrity_check == OK | ✅ |
| PRAGMA foreign_key_check == 0 | ✅ |
| Zero orphan rows | ✅ |
| Fact:evidence 1:1 | ✅ |
| Deterministic hashes | ✅ |
| Schema signature unchanged | ✅ |
| production.db remains untouched | ✅ |

---

## 7. Deliverables

| File | Path |
|------|------|
| Sprint 02 Report | `mr-kep/book_enrichment_sprint02/sprint02_report.md` |
| Coverage Delta | `mr-kep/book_enrichment_sprint02/coverage_delta.md` |
| Statistics | `mr-kep/book_enrichment_sprint02/output/enrichment_statistics.json` |
| Unresolved Entities | `mr-kep/book_enrichment_sprint02/output/unresolved_entities.csv` |
| Manual Review Queue | `mr-kep/book_enrichment_sprint02/output/manual_review_queue.csv` |

---

## 8. Provenance & Collision Note

Sprint 01 wrote citations with prefix `CIT_MW2019_` and book key derived from the raw
filename SHA-1. The World Atlas filename hash `a10b6a6cc9bc` **collides** with a
pre-existing mock book (`BK_a10b6a6cc9bc`) seeded by the original P103 ingestion. To
preserve uniqueness + full provenance without any schema change, Sprint 02 uses a
**source-scoped, collision-free key** `WAW2011_B2` and citation prefix `CIT_WAW2011_B2_`.

A first (faulty) B2 attempt wrote 1,999 rows under the collided identity; these were
surgically removed and verified to restore the clean Sprint 01 end-state before the
correct re-run. A second re-run (after a fact_id 1:1-with-evidence fix) left 1,999
stale old-format facts; these were also removed, leaving 2,045 correct 1:1 facts.

---

## 9. Verdict

**Status: SPRINT 02 COMPLETE — VERIFIED**

The World Atlas of Whisky (B2) was processed using the frozen, verified Sprint 01
extraction architecture. All outputs are staged in `knowledge.db` with complete,
source-scoped provenance. No production database was modified. Promotion requires a
separately-approved apply gate.

**No further source processing initiated** — awaiting user direction for Sprint 03.
