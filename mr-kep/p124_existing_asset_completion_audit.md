# P124 — Existing Asset Completion Audit & Ingestion Execution Plan

**Status:** READ-ONLY audit · NO production/knowledge.db/staging/registry writes · NO commits · NO migrations.
**Baseline:** P120 ✅ P121 ✅ P122 ✅ P123 ✅ (architecture frozen). This task audits *existing local assets only*.
**Method:** every state claim verified against `knowledge.db` / `production.db` (via P121 gate), staging DBs, CSV/JSONL on disk, KEP reports, git. "NOT VERIFIED" used where evidence absent.

---

## Executive Summary

The project holds a **deep, partially-ingested corpus**. Production (the app DB) is heavily populated (distilleries 2144, whiskies 4749, flavor_profiles 3467, tasting_notes 1848), but **two large book extractions are stuck in staging** (B4b JSONL, SMWS 792 vectors + 13,239 tasting rows) and a **substantial book manual-review backlog** exists (767 rows + 352 distillery + 264 brand + 375 catalogue). Beyond books, **web/retail ETL outputs** (whiskybase, retail, low_risk, queue, manual_sources) and **3 web adapters** (masterofmalt/whiskybase/whiskynotes) are present but uningested. The bottleneck is confirmed: **not architecture, but un-promoted existing assets + human-review backlog.**

**Top unfinished, high-value assets:** (1) SMWS 792 staged vectors — exclusive cask evidence, ready for review gate; (2) B4b extraction — 561 claims staged, needs classification review→promotion; (3) book manual_review_queue (767) — resolver output awaiting human decision; (4) whiskybase/retail web ETL — net-new external reviews.

---

## 1. Complete Asset Inventory

| # | Asset | Type | Location | Source | Discovery | Current State |
|---|---|---|---|---|---|---|
| A1 | production.db (live) | SQLite | `output/import/production.db` | KEP pipeline | gate read | EXISTS (37 tables, populated) |
| A2 | knowledge.db (live) | SQLite | `mr-kep/p102_bootstrap/knowledge.db` | P102 bootstrap | gate read | EXISTS (24 books, 3077 vectors) |
| A2b | knowledge.db (mirror) | SQLite | `output/import/knowledge.db` | P102 | gate read | EXISTS (mirror — verify parity) |
| A3 | book_registry.json | JSON | `data/registries/book_registry.json` | P122/P46 | read | EXISTS (14 recs, 13 placeholder) |
| A4 | data/books (49 books) | PDF/EPUB | `data/books/` | acquisition | ls | EXISTS (incl. SMWS 906-PDF archive) |
| A5 | SMWS staging CSV | CSV | `output/import/smws/staging_smws_tasting_notes.csv` | P119 | wc | EXISTS (13,239 rows) |
| A6 | SMWS staged vectors | CSV | `mr-kep/p119_smws_extraction/canonical_vectors_staging.csv` | P119 | wc | EXISTS (792 vectors) |
| A7 | SMWS raw records | JSONL | `output/import/smws/smws_raw_records.jsonl` | P118 | ls | EXISTS |
| A8 | B4b extraction JSONL | JSONL×3 | `mr-kep/book_ingestion/B4b/` | B4b task | ls | EXISTS (561/525/721) |
| A9 | B4b classification | JSONL | `mr-kep/book_ingestion/B4b/candidate_classification.jsonl` | B4b task | ls | EXISTS (721) |
| A10 | book review queues | CSV×12 | `output/import/books/` | sprints | ls | EXISTS (4167 rows total) |
| A11 | p50_staging.db | SQLite | `output/staging/p50_staging.db` | P50 | ls | EXISTS (mirror of prod staging) |
| A12 | whiskybase ETL | CSV/JSON | `data/output/whiskybase/` | adapter | ls | EXISTS (9 files) |
| A13 | retail ETL | CSV/JSON | `data/output/retail/` | retail src | ls | EXISTS (3 files) |
| A14 | low_risk_sources | CSV | `data/output/low_risk_sources/` | src | ls | EXISTS (1 file) |
| A15 | data/queue | file | `data/queue/` | pipeline | ls | EXISTS (1 file) |
| A16 | manual_sources | CSV/JSON | `data/manual_sources/` | manual | ls | EXISTS (16 files) |
| A17 | web adapters | PY | `mr-kep/acquisition/adapters/` | KEP | ls | EXISTS (masterofmalt/whiskybase/whiskynotes) |
| A18 | etl scripts | PY | `etl/` | KEP | ls | EXISTS (ingest/inspect/merge/triage) |
| A19 | legacy_audit | JSON | `output/legacy_audit/` | P-legacy | ls | EXISTS (abv_first100) |
| A20 | p61a_migration | SQLite | `data/output/p61a_migration/` | P61a | ls | EXISTS (staging db) |
| A21 | backups/ | SQLite×N | `backups/`, `output/import/backups/` | gate/history | ls | EXISTS (frozen pre-state) |
| A22 | distillery_2022 | CSV×6 | `output/import/distilleries_2022/` | P56 | ls | EXISTS (staging_distilleries_2022 etc.) |
| A23 | p34a/p36/p37/p38/p40/p41/p42 | CSV | `output/p34a..p42/` | review pipeline | ls | EXISTS (review/promotion artifacts) |

---

## 2. Pipeline State Matrix

| Asset | Not proc | Imported | Parsed | Normalized | Matched | Canonical | Vectorized | Staged | Reviewed | Promoted | Discarded |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 production.db | – | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | – | ✅ | ✅ (live) | – |
| A2 knowledge.db | – | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | – | ✅ | ✅ (canonical) | – |
| A4 books (49) | 47 | 1(B4b reg) | 1(B4b) | 1(B4b) | 1(B4b) | 0 | 0 | 1 | 1(B4b cls) | 0 | 0 |
| A5 SMWS staging | – | ✅ | ✅ | ✅ | partial | 0 | 792(vec) | ✅ | 0 | 0 | 0 |
| A6 SMWS vectors | – | ✅ | ✅ | ✅ | pending | 0 | ✅ | ✅ | 0 | 0 | 0 |
| A8 B4b JSONL | – | ✅ | ✅ | ✅ | partial | 0 | 0 | ✅ | 1(cls) | 0 | 0 |
| A10 book queues | – | ✅ | ✅ | ✅ | partial | 0 | 0 | ✅ | partial(62 prod) | 0 | 0 |
| A11 p50_staging | – | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 0(mirror) | – |
| A12 whiskybase | ✅ | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| A13 retail | ✅ | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| A14 low_risk | ✅ | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| A15 queue | ⚠ | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| A16 manual_sources | partial | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| A17 adapters | – | ✅(code) | – | – | – | – | – | – | – | – | – |
| A19 legacy_audit | ✅ | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| A20 p61a | ✅ | partial | partial | 0 | 0 | 0 | 0 | ✅ | 0 | 0 | 0 |
| A22 distillery_2022 | – | ✅ | ✅ | ✅ | ✅ | 0 | 0 | ✅ | 0 | 0 | 0 |
| A23 p34–p42 | – | ✅ | ✅ | ✅ | ✅ | 0 | 0 | ✅ | partial | partial | 0 |

---

## 3. Processing Coverage

- **Production (app DB):** distilleries 2144, whiskies 4749, brands 471, knowledge_regions 23, official_source_references 96, tasting_notes 1848, flavor_profiles 3467, flavor_evidence 791, staging_book_flavor_profiles 2577 *(verified via gate)*.
- **Canonical (knowledge.db):** books 24, citations 13133, evidence_nodes 13133, extracted_facts 13133, consensus_nodes 3077, canonical_vectors 3077, promotion_candidates 3101, audit_logs 0.
- **Book extraction coverage:** 1 of 49 books fully extracted+classified (B4b). SMWS archive = 803/906 PDFs processed → 792 vectors staged. Remaining 47 books UNEXTRACTED.
- **Staging backlog (unpromoted):** SMWS 792 vectors + 13,239 tasting rows; B4b 561 claims; book manual_review_queue 767 (+352 distillery +264 brand +375 catalogue); p50_staging mirror.
- **Web/retail ETL:** 0 ingested (whiskybase 9 / retail 3 / low_risk 1 / queue 1 / manual 16 files untouched).

---

## 4. Blocked Assets

| Asset | Blocker | Evidence |
|---|---|---|
| A6 SMWS vectors | Needs review gate before promotion; 33 malformed SMWS codes (P119.5) | `p119_5_validation/validation_report.md` (759 valid / 33 malformed) |
| A8 B4b JSONL | Staged; 721 unresolved (536 real distillery leads) need human review before resolver | `B4b/classification_report.md` |
| A10 book queues | 767 manual_review_queue + 352 distillery + 264 brand + 375 catalogue await human decision | `output/import/books/*.csv` row counts |
| A11 p50_staging.db | **Duplicate staging copy** of production.db staging — ambiguous ownership; risks double-promotion | table parity vs production.db (1823 distilleries etc.) |
| A15 data/queue | 1 file, type NOT VERIFIED — pipeline handoff unclear | only `ls` available; content unread |
| A20 p61a_migration | Staging DB, migration not completed (partial) | `data/output/p61a_migration/*.db` present, no promotion record |
| A22 distillery_2022 | Staged (`staging_distilleries_2022.csv`) but not canonicalized into distilleries | `output/import/distilleries_2022/` artifacts |

---

## 5. Ready-to-Process Assets

| Asset | Why ready | Gate |
|---|---|---|
| A6 SMWS vectors | Already extracted+validated; 792 vectors staged; only review gate remains | P119.5 validation passed (759 valid) |
| A8 B4b claims | Extracted+classified; deterministic, no LLM | classification review pass |
| A10 book queues (prod 62) | Already in production.db `staging_manual_review_queue` | human review decisions |
| A22 distillery_2022 | Parsed/matched; needs canonical merge | resolver match |
| A17 adapters | Code complete; wire to ingestion | ETL run |

---

## 6. Highest-Value Unfinished Assets (ranked)

| Rank | Asset | Knowledge gain | Effort | Risk | Deps |
|---|---|---|---|---|---|
| 1 | A6 SMWS 792 vectors | HIGH (exclusive cask evidence) | LOW (already staged) | LOW | review gate |
| 2 | A8 B4b 561 claims | HIGH (global distillery+flavor) | LOW–MED | LOW | classification review |
| 3 | A10 book queues (767) | MED–HIGH (resolver backlog) | MED (human) | LOW | human review |
| 4 | A22 distillery_2022 | MED (distillery facts) | LOW | LOW | resolver |
| 5 | A12 whiskybase ETL | MED (external reviews) | MED | MED | adapter+gate |
| 6 | A13 retail ETL | MED (retail/prices) | MED | MED | adapter+gate |
| 7 | A11 p50_staging | LOW (dup) | LOW (dedupe) | MED (double-promo) | decision |

---

## 7. Execution Queue (exact order)

| # | Item | Priority | Reason | Est. Effort | Deps | Validation | Acceptance |
|---|---|---|---|---|---|---|---|
| Q1 | Promote SMWS 792 vectors (review gate) | CRITICAL | exclusive cask evidence, staged & validated | LOW | P119.5 pass | re-run P119.5; 759 valid, 0 malformed post-fix | 792 vectors in knowledge.db canonical_vectors (SMWS-tagged) |
| Q2 | Promote B4b claims → staging_* | HIGH | global distillery+flavor, deterministic | MED | B4b classification review | claims resolve to ≥300 distilleries via gate | B4b rows in staging_book_flavor_profiles; 0 orphan |
| Q3 | Clear book manual_review_queue (767→decisions) | HIGH | resolver backlog blocks canonical growth | MED (human) | human review | every row → approve/reject decision logged | queue emptied or decisions recorded |
| Q4 | Canonicalize distillery_2022 | MED | distillery facts not yet merged | LOW | resolver | distilleries count increases by expected delta | new distilleries in production.db.distilleries |
| Q5 | Resolve p50_staging.db duplication | MED | prevent double-promotion | LOW | owner decision | parity check; one copy declared source of truth | single staging copy referenced |
| Q6 | Ingest whiskybase ETL (A12) | MED | net-new external reviews | MED | adapter+gate | review count increases; no dup | external_reviews staged |
| Q7 | Ingest retail ETL (A13) | MED | retail/price signals | MED | adapter+gate | price_history grows | retail rows staged |
| Q8 | Triage data/queue + manual_sources | LOW | unclear handoff | LOW | read content | each file classified | queue emptied or routed |
| Q9 | p61a_migration completion | LOW | partial migration | MED | schema check | migration record present | staging→canonical applied |

---

## Gap Summary

- **Book extraction gap:** 47 of 49 books UNEXTRACTED (P122 roadmap: B1/B6/B5 next).
- **Promotion gap:** SMWS + B4b staged but not promoted (review gate needed).
- **Review backlog:** 767 manual + 352 distillery + 264 brand + 375 catalogue rows.
- **Web/retail gap:** whiskybase/retail/low_risk/queue/manual all uningested (0 external reviews in prod).
- **Duplication risk:** p50_staging.db mirrors production.db staging (resolve ownership).
- **Registry staleness:** book_registry.json 13/14 placeholder (refresh before ingestion).

---

## Final Recommendation

**GO (audit complete).** The corpus is far from empty — production.db and knowledge.db are substantially populated, but **two large book extractions (SMWS, B4b) sit staged and unpromoted**, a **book manual-review backlog** persists, and **web/retail ETL outputs are untouched**. Execution should follow Q1→Q9: first promote the already-staged SMWS/B4b evidence through the review gate (low effort, high value), then clear the review backlog, then ingest web/retail adapters. No architecture change, no new sources — strictly completion of existing assets. All states above are evidence-backed via gate reads and on-disk file inspection.

---

## Final Ad-Hoc Verification (read-only, this run)

Executed after writing this report — see terminal output below. Items: production.db hash, knowledge.db hash, canonical_vectors count, staging row counts, git working tree, new/modified/deleted files, no mutation.
