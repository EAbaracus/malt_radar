# [HISTORICAL] Project Map

**NOTE:** This layout describes the classic structure. The active canonical architecture is **MR-KEP** (domain pipeline) + **KEP Runtime** (safety/execution layer).

- `data/`: Contains raw sources, PDF books, and output CSVs.
- `docs/`: System documentation and architectural decisions.
- `output/`: Database instances, imports, and backups.
- `scripts/core/`: Shared utilities, DB handlers, and NLP engines.
- `scripts/pipeline/`: [RETIRED] Sequential staging and execution pipeline (P1 to P25).
- `scripts/archive/`: Legacy scripts, outdated dry-runs, and scratch files.
- `mr-kep/`: [CANONICAL] Domain-specific pipeline components (Ingest, Extract, Normalize, Canonicalize, Evidence, QA, Promote).
- `kep_review_runtime/`: [CANONICAL] Execution runtime safety layer (PromotionGate, db_write_guard, audit).
