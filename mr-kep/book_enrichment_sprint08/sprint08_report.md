# Book Enrichment Sprint 08 — Report

**Source:** Whisky: The Manual (Dave Broom, 2014)
**Source ID (source-scoped):** `DB_MANUAL`  (EPUB)
**Run ID:** `RUN_ENRICHMENT_DBM_20260715_162033`
**Duration:** 0.00s
**Timestamp:** 2026-07-15T16:23:22.747943Z

---

## 1. Source Selection

Per the user directive, Sprint 08 processes **Dave Broom's "Whisky: The Manual" (2014)**
as source `DB_MANUAL`. This is an **EPUB** — the first non-PDF source in the S01-S08
series. It expands knowledge.db coverage and canonical flavor intelligence using verified
external historical tasting records.

The frozen Sprint 01 enrichment extractor/resolver/consensus functions were reused
**unchanged**. The **existing EPUB extraction stack** (`scripts/manual_sources/
extract_epub_text.py` — ebooklib + BeautifulSoup) was reused to convert the EPUB into the
per-document text chunks that the frozen `extract_entities` consumes. A source-scoped,
collision-free DB loader was written for Sprint 08 with **NO INSERT OR IGNORE** (per user
constraint): plain INSERT inside a single `BEGIN IMMEDIATE` transaction; any FK/UNIQUE
violation triggers **rollback + crash**. No previous consensus was overwritten (IDs are
unique per (whisky_id, algorithm_version)).

## 2. Inventory

- **EPUB documents/chunks:** 219 (non-empty 219)
- **Total characters:** 301,873
- **Lexicon (production.db, read-only):** 13,330 entries
- **Extraction stack:** existing ebooklib+BeautifulSoup

## 3. Extraction & Resolution

| Metric | Value |
|--------|-------|
| Total entities matched | 197 |
| Resolved to whisky_id | 126 |
| Unresolved (distillery/partial) | 71 |
| Resolution rate | 64.0% |

## 4. Knowledge.db Delta

| Table | Inserted |
|-------|:-----:|
| books | +1 |
| book_versions | +1 |
| citations | +444 |
| evidence_nodes | +444 |
| extracted_facts | +444 |
| consensus_nodes | +126 |
| canonical_vectors | +126 |
| promotion_candidates | +30 |
| **New whisky_ids covered** | **+1** |

## 5. Coverage Dashboard (Cumulative S01-S08)

- **Total whisky coverage:** 1737 distinct whisky_ids
- **Newly covered this sprint:** 1
- **New citations:** 444
- **New evidence_nodes:** 444
- **New extracted_facts:** 444
- **New canonical_vectors:** 126
- **Coverage percentage:** 48.83% of 3557 universe
- **Manual review backlog:** 71 unresolved entities

## 6. Validation Results

| Check | Result |
|-------|--------|
| PRAGMA integrity_check == OK | True |
| PRAGMA foreign_key_check == 0 | True |
| Zero orphan rows | True |
| Fact:evidence 1:1 | True |
| Schema signature unchanged | True |
| Previous consensus NOT overwritten | YES |
| production.db untouched | YES |
| Status='ACTIVE' on new records | YES |
| NO INSERT OR IGNORE used | YES (crash+rollback on violation) |

## 7. Deliverables

| File | Path |
|------|------|
| Sprint 08 Report | `mr-kep/book_enrichment_sprint08/sprint08_report.md` |
| Coverage Delta | `mr-kep/book_enrichment_sprint08/coverage_delta.md` |
| Statistics | `mr-kep/book_enrichment_sprint08/output/enrichment_statistics.json` |
| Unresolved Entities | `mr-kep/book_enrichment_sprint08/output/unresolved_entities.csv` |
| Manual Review Queue | `mr-kep/book_enrichment_sprint08/output/manual_review_queue.csv` |
| Integrity Hash | `mr-kep/book_enrichment_sprint08/output/integrity_hash.json` |

## 8. ID Scheme & Provenance

All DB_MANUAL rows carry source-scoped deterministic IDs (mandatory rules):
- `citation_id = CIT_DB_MANUAL_{entity}_{chunk}`
- `evidence_id = EV_DB_MANUAL_{sha1(citation_id)[:12]}`
- `fact_id    = FACT_DB_MANUAL_{entity}_{chunk}`
- `consensus_id = CONS_{whisky_id}_DB_MANUAL`  (algorithm_version `db_manual`)
- `vector_id = VEC_{whisky_id}_DB_MANUAL`

EPUB has no page numbers, so a **global chunk counter** spans all documents, keeping
the chunk index unique (same entity in two documents no longer collides). Every new
evidence/fact/consensus row has `status='ACTIVE'`. `source_hash` captured per citation for
immutable provenance. The complete chain is preserved:
books -> book_versions -> citations -> evidence_nodes -> extracted_facts ->
consensus_nodes -> canonical_vectors.

## 9. Verdict

**Status: SPRINT 08 COMPLETE — VERIFIED**

Dave Broom's "Whisky: The Manual" (DB_MANUAL) was processed using the frozen, verified
Sprint 01 extraction architecture plus the existing EPUB extraction stack. All outputs are
staged in `knowledge.db` with complete, source-scoped, immutable provenance and
`status='ACTIVE'`. No production database was modified. No INSERT OR IGNORE was used; the
load is crash-safe (rollback on violation). Previous consensus was not overwritten.
Promotion requires a separately-approved apply gate.

**No further source processing initiated** — Sprint 08 stop gate reached. Awaiting user
direction.
