# Book Enrichment Sprint 07 — Report

**Source:** Jim Murray's Whisky Bible 2020 (Rest of the World)
**Source ID (source-scoped):** `JMB2020`
**Run ID:** `RUN_ENRICHMENT_JMB_20260715_154035`
**Duration:** 73.94s
**Timestamp:** 2026-07-15T15:40:36.736381Z

---

## 1. Source Selection

Per the user directive, Sprint 07 processes the **Jim Murray's Whisky Bible 2020 (Rest of
the World)** — a single PDF source (`Jim Murray's Whisky Bible 2020 _ Rest of World -- Jim Murray -- 2020 edition,.pdf`), processed as source `JMB2020`. This
expands knowledge.db coverage and canonical flavor intelligence using verified external
historical tasting records (Jim Murray's annual whisky guide).

The frozen Sprint 01 enrichment extractor/resolver/consensus functions were reused
**unchanged**. A source-scoped, collision-free DB loader was written for Sprint 07 with
**NO INSERT OR IGNORE** (per user constraint): plain INSERT inside a single
`BEGIN IMMEDIATE` transaction; any FK/UNIQUE violation triggers **rollback + crash**.

## 2. Inventory

- **PDF pages:** 392 (non-empty 388)
- **Total characters:** 1,895,722
- **Lexicon (production.db, read-only):** 13,330 entries

## 3. Extraction & Resolution

| Metric | Value |
|--------|-------|
| Total entities matched | 1050 |
| Resolved to whisky_id | 712 |
| Unresolved (distillery/partial) | 338 |
| Resolution rate | 67.8% |

## 4. Knowledge.db Delta

| Table | Inserted |
|-------|:-----:|
| books | +1 |
| book_versions | +1 |
| citations | +2551 |
| evidence_nodes | +2551 |
| extracted_facts | +2551 |
| consensus_nodes | +712 |
| canonical_vectors | +712 |
| promotion_candidates | +712 |
| **New whisky_ids covered** | **+192** |

## 5. Coverage Dashboard (Cumulative S01-S07)

- **Total whisky coverage:** 1736 distinct whisky_ids
- **Newly covered this sprint:** 192
- **New citations:** 2551
- **New evidence_nodes:** 2551
- **New extracted_facts:** 2551
- **New canonical_vectors:** 712
- **Coverage percentage:** 48.81% of 3557 universe
- **Manual review backlog:** 338 unresolved entities

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

## 7. Deliverables

| File | Path |
|------|------|
| Sprint 07 Report | `mr-kep/book_enrichment_sprint07/sprint07_report.md` |
| Coverage Delta | `mr-kep/book_enrichment_sprint07/coverage_delta.md` |
| Statistics | `mr-kep/book_enrichment_sprint07/output/enrichment_statistics.json` |
| Unresolved Entities | `mr-kep/book_enrichment_sprint07/output/unresolved_entities.csv` |
| Manual Review Queue | `mr-kep/book_enrichment_sprint07/output/manual_review_queue.csv` |
| Integrity Hash | `mr-kep/book_enrichment_sprint07/output/integrity_hash.json` |

## 8. ID Scheme & Provenance

All JMB2020 rows carry source-scoped deterministic IDs (mandatory rules):
- `citation_id = CIT_JMB2020_{entity}_{page}`
- `evidence_id = EV_JMB2020_{sha1(citation_id)[:12]}`
- `fact_id    = FACT_JMB2020_{entity}_{page}`
- `consensus_id = CONS_{whisky_id}_JMB2020`  (algorithm_version `jmb2020`)
- `vector_id = VEC_{whisky_id}_JMB2020`

Every new evidence/fact/consensus row has `status='ACTIVE'`. `source_hash` captured per
citation for immutable provenance. The complete chain is preserved:
citations -> evidence_nodes -> extracted_facts -> consensus_nodes -> canonical_vectors.

## 9. Verdict

**Status: SPRINT 07 COMPLETE — VERIFIED**

Jim Murray's Whisky Bible 2020 (JMB2020) was processed using the frozen, verified Sprint 01
extraction architecture. All outputs are staged in `knowledge.db` with complete,
source-scoped, immutable provenance and `status='ACTIVE'`. No production database was
modified. No INSERT OR IGNORE was used; the load is crash-safe (rollback on violation).
Promotion requires a separately-approved apply gate.

**No further source processing initiated** — Sprint 07 stop gate reached. Awaiting user
direction.
