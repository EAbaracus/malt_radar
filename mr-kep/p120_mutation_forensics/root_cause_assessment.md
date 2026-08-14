# Root Cause Assessment — `production.db` Mutation (P120 Forensic)

_READ-ONLY. Conclusion based on fingerprint, timeline, process analysis, and code search._

## What happened
Between 20:21 and 21:17 on 2026-07-15, `production.db` received **three bulk
append bursts** adding **+1,192** whisky rows (`data_confidence=NULL`), on top of a
pre-existing curated batch (+264 `medium` before session). Net since the Jul-9
backup: +1,456 rows (3,293 → 4,749). Three existing rows were region-enriched
(additive). No rows deleted; no identity/score fields altered.

## Origin
- **Not the P120/P103 audit** — all audit scripts are `?mode=ro` (verified).
- **Not Git** — `output/` is gitignored; no commit touched the DB.
- **Not the Flutter app** — no `dart`/`flutter` process running.
- **Not the FastAPI backend** — no listener on `:8080`.
- **Not a streaming/service writer** — bursts are discrete, then silence.
- **Most consistent with:** a **deterministic bulk CSV→production importer**
  (class `etl/ingest_whisky_database.py` / `scripts/72_production_import_seeder.py`
  or equivalent) executed manually. Shape matches: legacy `W<3+ digits>` IDs,
  realistic catalogue names, NULL confidence/distillery, no abv/brand.

## Confidence
- **High** — mutation is a deterministic bulk importer (not random, not a runtime
  service, not the audit).
- **Medium** — exact script identity unconfirmed. The writer process had already
  exited before observation; the DB has no self-logging of the import
  (`source_audit` was not populated by these writes), so attribution rests on code
  search + row shape, not a captured process.

## Current state
Writer has **terminated**; DB stable at 4,749 (mtime 21:17:54, no journal, two
consecutive steady reads). Risk of *further* uncontrolled mutation is currently
low, but the source was never positively identified and could re-run.

## Why this matters for ingestion
The coverage denominator moved 3,557 → 3,876 → 3,959 → 4,749 during the audit.
Any coverage % computed against an earlier number is now stale. Sprint 08 (or any
ingestion) must be baselined against a **frozen, stable** `production.db`.
