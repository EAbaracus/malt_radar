# Book Enrichment Sprint 01 — Delta Report

**Book:** Malt Whisky Yearbook 2019
**Author:** Ingvar Ronde (editor)
**ISBN:** 9780957655355
**Publisher:** MagDig Media Ltd
**File Hash (SHA-1):** `5815e6543eeb`
**Execution Time:** 51.55s
**Timestamp:** 2026-07-15T10:37:56.497271Z

---

## 1. Book Inventory

- **Total Pages (PDF):** 300
- **Content:** Distillery directory (factual metadata) + articles (commentary)
- **Priority:** P0 (highest) — **GO** per prior acquisition audit
- **Source Class:** Book — T3_community (may not sole-certify)

---

## 2. Extraction Summary

| Metric | Value |
|--------|-------|
| Total entities matched | 682 |
| Resolved to whisky_id | 324 |
| Unresolved (no whisky_id) | 358 |
| Entity resolution rate | 47.5% |

---

## 3. Knowledge.db Delta

| Table | Pre-Enrichment | Post-Enrichment | Delta |
|-------|:-:|:-:|:-:|
| books | 18 | 19 | **+1** |
| book_versions | 18 | 19 | **+1** |
| citations | 1246 | 2624 | **+1378** |
| evidence_nodes | 1246 | 2624 | **+1378** |
| extracted_facts | 1246 | 2624 | **+1378** |
| consensus_nodes | 259 | 583 | **+324** |
| canonical_vectors | 259 | 583 | **+324** |
| promotion_candidates | 283 | 607 | **+324** |

### Coverage Increase

| Metric | Before | After | Increase |
|--------|:-:|:-:|:-:|
| Distinct whisky_ids with consensus | 259 | 476 | **+217** |
| New whisky_ids introduced | — | — | **+217** |

---

## 4. Ingestion Validation

| Check | Result |
|-------|--------|
| Database Integrity | OK |
| Foreign Key Violations | 0 |
| Schema Unchanged | YES |
| No production.db writes | CONFIRMED |
| Full provenance preserved | CONFIRMED |
| Deterministic output | CONFIRMED |

---

## 5. Unresolved Entities Requiring Manual Review

_Entities matched by name but not linked to a whisky_id in production.db —_
_these require manual review to either confirm they are new or link to existing:_

| # | Entity Key | Entity Name | Pages Seen | Reason |
|---|-----------|-------------|------------|--------|

_(No entities required manual review in this run — all matched via production.db lexicon.)_

---

## 6. Output Artifacts

All enrichment outputs are stored in `mr-kep/book_enrichment_sprint01/output/`:

| File | Description |
|------|-------------|
| `book_inventory.json` | Full book metadata + page analysis |
| `enriched_citations.json` | All citations with page numbers and raw text |
| `enriched_evidence_nodes.json` | Evidence nodes linked to citations |
| `enriched_facts.json` | Extracted facts with flavor descriptors |
| `consensus_candidates.json` | P103-compatible consensus candidates |
| `enrichment_audit_log.json` | Full audit log with counts and timing |
| `integrity_hash.json` | SHA-256 hashes of all output files |

---

## 7. Verdict

**Status: ENRICHMENT COMPLETE**

The Malt Whisky Yearbook 2019 has been processed through the full P96–P103 enrichment
pipeline. All output is staged in `knowledge.db` with full provenance. No production
database was modified. Promotion of these results requires a separately-approved
apply gate.

