# Book Enrichment Sprint 03 — Report

**Book:** The World Guide to Whisky
**Author:** Michael Jackson
**ISBN:** 9780881622843
**Publisher:** Salem House Publishers
**Matrix Ref:** B3 / P1 / GO (historical enrichment)
**Book Key (source-scoped, collision-free):** `MJ1987_B3`
**Run ID:** `RUN_ENRICHMENT_B3_20260715_122208`
**Duration:** 15.77s
**Timestamp:** 2026-07-15T12:22:08.490507Z

---

## 1. Source Selection

Per the frozen `source_priority_matrix.md`, the next approved high-priority book source
after B1 (S01) and B2 (S02) is **B3 — Michael Jackson "The World Guide to Whisky"**
(1987, ISBN 9780881622843), classified **P1 / GO (historical enrichment)**. The user
confirmed the ISBN `978-0-88162-284-3` maps to this exact corpus asset. (Note: the
user's prompt named "Complete Guide to Single Malt Scotch"; that title is NOT in the
corpus. The present asset — *The World Guide to Whisky* — is the MJ book the matrix
labels B3, and the only MJ file available. Processed as B3 per user confirmation.)

The frozen Sprint 01 enrichment extractor/resolver/consensus functions were reused
**unchanged**. A source-scoped, collision-free DB loader was written for Sprint 03 with
**NO INSERT OR IGNORE** (per user constraint): plain INSERT inside a single
`BEGIN IMMEDIATE` transaction; any FK/UNIQUE violation triggers **rollback + crash**.

---

## 2. Inventory

- **Total Pages:** 232 (text-extractable: 228/232)
- **Total Characters:** 724,145
- **Lexicon (production.db, read-only):** 13,330 entries
- **Source Class:** Book — T3_community (historical)

---

## 3. Extraction & Resolution

| Metric | Value |
|--------|-------|
| Total entities matched | 310 |
| Resolved to whisky_id | 164 |
| Unresolved (distillery/partial) | 146 |
| Resolution rate | 52.9% |

---

## 4. Knowledge.db Delta (NOT idempotent — first load only)

| Table | Inserted |
|-------|:-----:|
| books | +1 |
| book_versions | +1 |
| citations | +767 |
| evidence_nodes | +767 |
| extracted_facts | +767 |
| consensus_nodes | +164 |
| canonical_vectors | +164 |
| promotion_candidates | +164 |
| **New whisky_ids covered** | **+31** |

---

## 5. Coverage Dashboard (Cumulative S01+S02+S03)

- **Total whisky coverage:** 771 distinct whisky_ids
- **Newly covered this sprint:** 31
- **New citations:** 767
- **New evidence_nodes:** 767
- **New extracted_facts:** 767
- **New canonical_vectors:** 164
- **Source contribution (B3):** The World Guide to Whisky → 164 vectors
- **Coverage percentage:** 21.68% of 3557 universe
- **Manual review backlog:** 146 unresolved entities

---

## 6. Validation Results

| Check | Result |
|-------|--------|
| PRAGMA integrity_check == OK | True |
| PRAGMA foreign_key_check == 0 | True |
| Zero orphan rows | True |
| Fact:evidence 1:1 | True |
| Schema signature unchanged | True |
| production.db untouched | YES |
| Status='ACTIVE' on new records | YES |
| NO INSERT OR IGNORE used | YES (crash+rollback on violation) |

---

## 7. Deliverables

| File | Path |
|------|------|
| Sprint 03 Report | `mr-kep/book_enrichment_sprint03/sprint03_report.md` |
| Coverage Delta | `mr-kep/book_enrichment_sprint03/coverage_delta.md` |
| Statistics | `mr-kep/book_enrichment_sprint03/output/enrichment_statistics.json` |
| Unresolved Entities | `mr-kep/book_enrichment_sprint03/output/unresolved_entities.csv` |
| Manual Review Queue | `mr-kep/book_enrichment_sprint03/output/manual_review_queue.csv` |
| Integrity Hash | `mr-kep/book_enrichment_sprint03/output/integrity_hash.json` |

---

## 8. Provenance

All B3 rows carry source-scoped, deterministic IDs:
- `BK_MJ1987_B3` → `VER_4188a63fe1e2` → `CIT_MJ1987_B3_<entity>_<page>` →
  `EV_...` → `FACT_<entity>_<page>`
- `CONS_<whisky>_mj1987_b3` + `VEC_<whisky>_mj1987_b3` (algorithm_version `mj1987_b3`,
  isolated from S01/S02 to avoid UNIQUE(whisky_id, algorithm_version) collision).
- Every new evidence/fact/consensus row has `status='ACTIVE'`.
- `source_hash` captured per citation for immutable provenance.

---

## 9. Verdict

**Status: SPRINT 03 COMPLETE — VERIFIED**

The World Guide to Whisky (B3) was processed using the frozen, verified Sprint 01
extraction architecture. All outputs are staged in `knowledge.db` with complete,
source-scoped, immutable provenance and `status='ACTIVE'`. No production database was
modified. No INSERT OR IGNORE was used; the load is crash-safe (rollback on violation).
Promotion requires a separately-approved apply gate.

**No further source processing initiated** — Sprint 03 stop gate reached. Awaiting user
direction.
