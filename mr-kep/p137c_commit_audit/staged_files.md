# P137C — Staged Files

- generated for the single milestone commit (P136-P137B scope).
- ONLY the 5 paths below are intended for `git add`. Everything else in the
  repo is pre-existing (other sessions) and must stay unstaged.

## Intended staging set
```
mr-kep/CANONICAL_SCHEMA.md
mr-kep/decision_log.jsonl
mr-kep/p136_knowledge_bootstrap/
    migration/schema.sql
    migration/migration.sql
    runtime/migrate.py
    runtime/ingest.py
    tests/test_bootstrap.py
    documentation/er_diagram.md
    documentation/runtime_architecture.md
    documentation/ingestion_documentation.md
mr-kep/p137a_reconciliation/
    count_relationship.md
    crosswalk_necessity_assessment.md
    executive_summary.md
mr-kep/p137b_smws_promotion/
    export_generator.py
    promotion_export.csv
    conflict_report.csv
    coverage_delta.csv
    promotion_statistics.json
    promotion_manifest.json
    executive_summary.md
    promotion_statistics.md
    coverage_delta.md
    field_delta.md
    conflict_report.md
    validation.md
    export_manifest.md
mr-kep/p137c_commit_audit/
    commit_summary.md
    staged_files.md
    verification.md
    milestone.md
```

## Explicitly EXCLUDED (do not stage)
- `mr-kep/p111_*` `p118_*` `p119_*` `p120_*` `p121_*` `p122_*` `p123_*`
  `p124_*` `p125_*` `p126_*` `p127_*` `p128_*` `p129_*` `p130_*`
  `p131_*` `p132_*` `p133_*` `p134_*` `p135_*` — other sessions' work.
- `book_*` / `csv_intelligence_*` / `coverage_*` / `roi_*` / `source_intake_*`
  / `archive/` / `backups/` / `.agents/` — other sessions' artifacts.
- modified tracked: `.github/workflows/android-release.yml`, `.gitignore`,
  `memory/current-phase.md`, deleted `scripts/p53_*` — other sessions.
- `.pytest_cache/`, `backend/__pycache__/`, `archive/__pycache__/` — build strays.

## git add command (scope-only)
```
git add mr-kep/CANONICAL_SCHEMA.md mr-kep/decision_log.jsonl \
        mr-kep/p136_knowledge_bootstrap mr-kep/p137a_reconciliation \
        mr-kep/p137b_smws_promotion mr-kep/p137c_commit_audit
```
