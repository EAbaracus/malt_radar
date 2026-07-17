# Pipeline Status Report

This report tracks the status of each raw/external data source in the Malt Radar pipeline.

| Source | Discovered | Extracted | Resolved | Staged | Promoted | Blocked |
|---|---|---|---|---|---|---|
| **Books** | 49 | 46 (44 P125 + B4b + SMWS) | 59,708 mentions | 44 JSONL files in `p125/_evidence/` | 0 | 30,529 candidates await resolver review. |
| **NotebookLM** | Partial | Script only | 0 | 17 staging rows | 0 | Incomplete pipeline (no JSON export). |
| **SMWS** | 906 PDFs | 803 processed -> 792 vectors | 726 MERGE, 77 AMBIGUOUS (P127.5) | `canonical_vectors_staging.csv` (792), `tasting_notes.csv` (13k) | 790 entries (prod.db flavor_evidence) | Blocked from `knowledge.db` (P128 blockers). |
| **Wikipedia** | Wikipedia brand list | 64 rows | 0 | `staging_external_reviews_wikipedia_brands` | 0 | Queue ingestion not integrated. |
| **Whiskybase** | 9 files | Raw scrape | 0 | 0 | 0 | Untouched web ETL data. |
| **Whisky Advocate** | 11 PDF issues | Part of 44 books run | Partially | JSONL staging | 0 | Awaiting book resolver backlog clearance. |
| **GIS Assets** | Shapefiles | 0 | 0 | 0 | 0 | No shapefile reader implemented. |

## Source Pipeline Detail

### 1. Books (General Corpus)
- **Status:** Extracted but Unpromoted.
- **Details:** P125 successfully evaluated and extracted all 44 unprocessed single books (excluding B4b and SMWS). Over 59,708 mentions of known distilleries/whiskies were matched.
- **Blockers:** 30,529 new entity candidates are staged in `p125/_evidence/` but cannot be auto-promoted due to the lack of manual resolver validation.

### 2. SMWS Archive
- **Status:** Staged & Partially Promoted.
- **Details:** 803 PDFs parsed to extract 792 staged vectors and 13,239 tasting notes. P120 and P121 successfully promoted 790 entities and 791 evidence rows into the live `production.db`.
- **Blockers:** Staged vectors and tasting notes are blocked from promotion into `knowledge.db` due to schema incompatibility and the lack of a UUID bridge.

### 3. Web & Retail ETL (Whiskybase / Retail / Wikipedia)
- **Status:** Discovered & Scraped.
- **Details:** Scraped datasets (e.g., Whiskybase samples, retail CSVs) are stored on disk.
- **Blockers:** Ingestion pipelines are not hooked to the active promotion queues.
