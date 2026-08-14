# Phase Matrix — KEP & Ingestion Roadmap

This matrix represents the status of all KEP and database ingestion phases to date, verified against database records and workspace files.

| Phase | Description | Status | Target DB/Files | Verification | Notes |
|---|---|---|---|---|---|
| **Sprint 1** | Foundation & Skeleton | **Completed** | Schemas, AGENTS.md, docs | Git / file presence | Standards frozen. |
| **P102** | Bootstrap seed | **Completed** | `mr-kep/p102_bootstrap/knowledge.db` | Seed inspection (3077 vectors) | Basis of the knowledge graph. |
| **P112** | HTFW Intake | **Completed** | `production.db` | SQL query | Deterministic intake complete. |
| **P115** | ALKO Intake | **Completed** | `production.db` | SQL query | Deterministic intake complete. |
| **P117** | Vinmonopolet Intake | **Completed** | `production.db` | SQL query | Low-risk retail csv processed. |
| **P118** | SMWS Archive Audit | **Completed** | 803 PDFs audited | `p118_smws_reports.py` | Audited structures. |
| **P119** | SMWS Extraction | **Completed** | 792 staged vectors | CSV checks | Parsed successfully. |
| **P119.5** | SMWS Validations | **Completed** | Staging audit | `validation_report.md` | Identified 33 malformed codes. |
| **P119.6a** | SMWS Code Remediation | **Completed** | CSV files corrected | Validation scripts | 33 Grain whiskies cleared as valid. |
| **P120** | SMWS Promotion | **Completed** | `production.db` | SQL query (791 evidence rows) | Created `flavor_evidence` table. |
| **P121** | SMWS Distillery Link | **Completed** | `production.db` | SQL query (790 matched) | Fixed distillery matching issues. |
| **P122** | Corpus Intelligence Audit | **Completed** | 49 books, 40 domains | Design only / report | Outlined gap analysis. |
| **P123** | Pipeline Blueprint | **Completed** | Architecture spec | Design only / blueprint | Knowledge graph design. |
| **P124** | Existing Asset Audit | **Completed** | Review of staging assets | Design only / report | Highlighted staging bottleneck. |
| **P125** | Book Ingestion Eval | **Completed** | 44 books extracted | JSONL outputs in `_evidence/` | Extracted 59k mentions. |
| **P126** | Book Promotion Plan | **Completed** | Candidate priority | Design only / report | Identified overlap vs prod. |
| **P127** | Entity Resolution Prep | **Completed** | 48k candidate mentions | Staged resolver stats | 16k merge, 10k create, 3.5k ambiguous. |
| **P127.5** | SMWS Bucket Prep | **Completed** | SMWS staging buckets | `smws_bucket_eligibility.md` | 726 merge, 77 ambiguous. |
| **P128** | SMWS Staging Preflight | **Completed** | Preflight checks | **NO-GO Verdict** | Blocked on empty knowledge.db, crosswalk gaps. |
| **P130** | Ground Truth Audit | **In Progress** | Project status | This audit | Current state verified. |

## Defunct/Abandoned Assets
- **`p50_staging.db`:** Outdated database from Sprint 50. Ambiguous ownership, superseded by `production.db`'s live staging. Replaced by production migrations.
- **`manual_curated_tasting_notes_url_extract_draft.csv`:** Skipped per `execution_order.md` due to low value (1 entity).
