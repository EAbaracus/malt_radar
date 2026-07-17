# P121 — Phase 4: Architectural Gap Assessment

## Question
Does `production.db` currently have **more than one legitimate write path** (anything other than the future P97/P98 promotion gate that can INSERT/UPDATE `production.db`)?

## Answer: **YES — multiple ungated write paths exist. This is an OPEN ARCHITECTURAL RISK.**

The intended design (per P100/P101/P102 "immutable knowledge database" + future P97/P98 promotion gate) is that `production.db` is mutated **only** through a single, audited promotion gate. In reality, at least **four** independent code paths can open `production.db` read-write and INSERT/UPDATE today:

1. `etl/ingest_whisky_database.py` — RW, bulk ETL (currently targets `whisky_products` but the connection is unguarded and would write `whiskies` if pointed at it).
2. `scripts/72_production_import_seeder.py` — RW, bulk `whiskies` seeder (guarded only by an in-script `stop_import` flag, not by any external gate).
3. `mr-kep/resolution/upsert_resolver.py` — RW `whiskies` UPSERT (dead code today, but the path exists and is ungated).
4. `backend/app/services/review_query_service.py` — RW `review_actions` + staging (an API-driven write path with no promotion-gate coupling).

There is **no isolation mechanism**: no DB-level user/role separation, no `PRAGMA query_only`, no file-level read-only lock in normal operation, no single chokepoint. Any of these scripts (or a future one) can write `whiskies` with `data_confidence=NULL` outside the gate — exactly what produced the 1,192+ NULL rows observed in P120.

## Explicit statement (for the promotion-gate architecture)
> **Any promotion-gate discipline built in P100/P101/P102 is currently MEANINGLESS if another script can write to `production.db` outside the gate.** The gate is not the only writer; it is one of several. Until every non-gate write path is either removed, redirected to a separate staging DB, or wrapped behind the same gate, the "immutable / single-write-path" guarantee the architecture claims does not hold.

## Recommended isolation measures (for the user to action — NOT executed here, read-only investigation)
- Demote `production.db` to read-only (`PRAGMA query_only=ON` or filesystem read-only) during normal operation; require an explicit, logged "promotion window" to flip it writable.
- Funnel **all** `whiskies` writes through one module (e.g. the P97/P98 gate); delete or quarantine `72`, `UpsertResolver`, and the ETL direct connection.
- Make the backend API (`review_query_service`) write only to staging/review tables, never to `whiskies`.
- Add a startup assertion that fails fast if more than one write path is live.

## Gate trigger status
The task says: STOP if "more than one legitimate write path to production.db is confirmed and no isolation mechanism exists." → **This condition is met.** Multiple ungated write paths are confirmed; no isolation exists. Investigation stops here per the gate and returns a **NO-GO** (see `p121_final_recommendation.md`). No database was modified, no process was killed.
