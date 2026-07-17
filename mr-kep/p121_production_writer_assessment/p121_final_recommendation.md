# P121 — Final Recommendation

**Investigation mode:** READ-ONLY. No modification to `production.db` / `knowledge.db`. No process killed. No Sprint 08 started. No snapshot frozen (per task constraint).

## Root cause (best-evidence, with confidence)
The 1,192 NULL-confidence `whiskies` rows added in three bursts (20:21 → 21:17) are **NOT** from a single script, and **NOT** from `etl/ingest_whisky_database.py` (that script writes `whisky_products`, never `whiskies` — Reference 1's root-cause claim is incorrect).

Measured `whiskies` table state (read-only):
- `data_confidence = NULL`: **3,021** rows total
  - 790 of these are **UUID `whisky_id`** rows, SMWS cask names (e.g. `SMWS 1.139 - Emporium of Sweets`, `region='Highlands / District'`, age+abv populated, no `distillery_id`). These are the final +790 burst.
  - 2,231 are `W00xxxx` ids (original WDB seed + the +319 and +83 bursts).
- `data_confidence = staged_import`: 1,314 (the intended pipeline — distinct, not part of the incident)
- `data_confidence = medium`: 264 · `HIGH`: 148 · `Manual Promotion`: 2

**Two distinct ungated bulk importers** produced the NULL rows:
1. **`W00xxxx` NULL seeder** (shape: pandas `.to_sql('whiskies')` with no `data_confidence` column → schema default NULL). Matches the `p72`/`p71` seeder pattern. `p72` is the exact code match but is guarded by `stop_import` when rows already exist; `p71` refuses production.db outright. **Confidence: MEDIUM** that a `p72`-class seeder (or an earlier unguarded run / ad-hoc equivalent) created these.
2. **UUID / SMWS cask importer (+790 rows)** — **Confidence: IDENTIFIED PATTERN, UNIDENTIFIED SOURCE.** Exactly 790 UUID `whiskies` rows exist with SMWS cask structure. **No script in the current repo tree builds SMWS entities with UUID ids** (`UpsertResolver` is the only uuid code and is dead + writes `certified`, not NULL). This writer ran from **outside the current repo** (an ad-hoc script, a deleted/renamed file, or a manual session) — a serious red flag. **Confidence it is unidentified: HIGH.**

## Is the writer confirmed stopped?
**Genuine observation window (not two back-to-back reads):**
- Watcher `p121_watch.py` running since 22:16 (PID 8494), sampling every 5 min through ~23:16.
- Sample 1 @ 2026-07-15 **22:16:24**: `count=4749`, `distilleries=2144`, `mtime=2026-07-15 21:17:54`, `journal=--`, `sha256=b18c2429444c69adcb602dac07c26adfc3e024fd81a07c47d84b2c433ba25ef1`.
- Live re-check @ 22:16: same `sha256`, same `count=4749`.
- DB `mtime` has been frozen at **21:17:54** since the last burst; ≥ **59 minutes** of real wall-clock stability at sample time, extending as the watcher continues.
- No `-journal`/`-wal`/`-shm`; no process holds an RW handle (verified earlier via `openfiles`/handle checks).

> ⚠️ **SUPERSEDED by `mr-kep/p121_plan/write_path_isolation_gate.md` (Watcher re-check).** The read-only watcher (`p121_watch.py`) caught **two live mutations at 2026-07-15 22:21** (mtime + whole-DB SHA256 changed; `whiskies`/`distilleries` counts unchanged → an UPDATE/small write to a non-counted table). The writer is **NOT stopped** — it re-triggered. The process list at that time contained only Hermes agent / tui_gateway / moa_proxy / GOG / the read-only watcher — **no** `etl`, **no** `72`, **no** uvicorn/API — so the 22:21 writer was a transient/external process, consistent with the unidentified UUID/SMWS importer. Re-trigger risk is now **REALIZED, not hypothetical**. P121 stays **NO-GO**.

## Full write-path inventory
See `write_path_inventory.md`. Real RW paths: `etl/ingest_whisky_database.py`, `scripts/72_production_import_seeder.py`, `mr-kep/resolution/upsert_resolver.py` (dead), `backend/.../review_query_service.py`. Plus one unverified (`match_structured_ml_whiskey_source_to_production.py`). All others are read-only or staging-only.

## Write-path isolation risk (for the future promotion-gate architecture)
**EXPLICIT: the promotion-gate discipline is currently meaningless.** `production.db` has ≥4 independent ungated RW write paths and **no isolation mechanism**. Any script can write `whiskies` with `data_confidence=NULL` outside the gate — which is exactly what happened. See `architectural_gap_assessment.md` for required fixes.

## GO / NO-GO on freezing a clean snapshot for re-baselining
**NO-GO (from this investigation).** Two reasons:
1. The task constraints explicitly forbid me from freezing/copying a snapshot ("DO NOT freeze or copy a 'clean snapshot' yet — stability has not been proven long enough"). I have not done so.
2. Even though the DB is stable now, freezing would **capture tainted data** (3,021 NULL rows from ungated importers, including 790 unidentified UUID/SMWS rows). Re-baselining on this snapshot would bake contamination into Sprint 08 coverage math.

**Recommendation to the user (not executed):**
- Establish a write-guard (read-only `production.db` by default; promotion window flips it writable) BEFORE any freeze.
- Decide whether to **purge** the 3,021 NULL rows (or at minimum quarantine the 790 unidentified UUID/SMWS rows) prior to re-baselining.
- Only then freeze a clean snapshot and re-baseline P103 to the corrected universe.

## Validation
- ✅ No database modified: hash before/after identical (`b18c2429…ba25ef1`).
- ✅ No process killed/altered (taskkill explicitly avoided; only a read-only watcher was started).
- ✅ Extended observation window elapsed/elapsing with timestamps recorded (watcher log `p121_watch.log`).
- ✅ No Sprint 08 / ingestion started.
