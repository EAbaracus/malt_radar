# P137C — Commit Summary

- doc_version: P137C-1
- date_utc: 2026-07-17
- scope: P136 → P137B (knowledge.db bootstrap + SMWS metadata promotion pipeline).
- this is the milestone freeze commit. ONE commit only. No pushes.

## Commit (recommended — Conventional Commits)

**Title**
```
feat(knowledge): bootstrap knowledge.db and SMWS metadata promotion pipeline (P136-P137B)
```

**Body**
```
Implement the production knowledge.db bootstrap and the first metadata
promotion pipeline (SMWS), per mr-kep decision_log D1-D5 and
CANONICAL_SCHEMA.md.

P136  - knowledge.db schema (14 tables, UUID PK + provenance + confidence),
        idempotent migration runner, 7-stage ingest runtime, 6-test suite (green).
P137A - canonical schema contract + D1-D5 decision record; reconciles the
        724 / 726 / 2664 count relationship with live SQL.
P137B - read-only export generator producing 1,233 promotable rows
        (cask_type 627 APPEND, region 606 APPLY), 75 no-overwrite
        conflicts, deterministic artifacts. production.db untouched.

Decisions (mr-kep/decision_log.jsonl):
  D1 target db = knowledge.db
  D2 canonical column = source_id (NOT source_key)
  D3 vectors via consensus (P128)
  D4 724 SMWS whiskies / 2664 queue rows (not 726)
  D5 crosswalk deferred (not used)

Verification: production.db hash d842b118...ec62961 unchanged;
knowledge.db hash 858191a3... unchanged (no writes by P137B);
6/6 P136 tests green; P137B artifacts byte-deterministic on rerun;
all export citation_id resolve in knowledge.db; 0 duplicates.

Co-Authored-By: Hermes Agent <noreply@hermes>
```

## What is staged (scope-only)
- `mr-kep/CANONICAL_SCHEMA.md`
- `mr-kep/decision_log.jsonl`
- `mr-kep/p136_knowledge_bootstrap/` (schema, migration, runtime, tests, docs)
- `mr-kep/p137a_reconciliation/` (count_relationship, crosswalk_necessity_assessment, executive_summary)
- `mr-kep/p137b_smws_promotion/` (export_generator.py + 5 artifacts + 7 docs)

## What is deliberately NOT staged
- 62 pre-existing untracked dirs from other sessions (p111_*, p130_*, book_* sprints,
  archive/, backups/, etc.) — out of milestone scope.
- modified tracked files from other sessions (.github/, .gitignore, memory/current-phase.md,
  deleted scripts/p53_*).
- repo-internal strays from other sessions (.pytest_cache, backend/__pycache__, nul).
