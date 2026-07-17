# P121 — Phase 3: Write-Path Inventory (production.db)

**Definition:** every script/process that opens `output/import/production.db` with a **read-write** connection, regardless of whether it currently issues writes. Connection mode read from source (or confirmed via `?mode=ro` / RW open).

| # | Path | Opens production.db RW? | What it's for | Currently writes? | Could it produce the observed pattern? (bulk, NULL-confidence, additive-only, silent) |
|---|------|------------------------|---------------|-------------------|---------------------------------------------------|
| 1 | `etl/ingest_whisky_database.py` | **YES** (line 9 `db_path`, line 179 `sqlite3.connect(db_path)` RW) | Bulk ETL of distilleries/countries/regions + `whisky_products` | Only if run | ❌ **NO** — writes table `whisky_products`, never `whiskies`. Cannot create the NULL `whiskies` rows. Reference 1's "root cause = this script" is **incorrect**. |
| 2 | `scripts/72_production_import_seeder.py` | **YES** (execute mode, line 192 `to_sql('whiskies', append)`) | Bulk CSV→production seeder | Only if `--execute` | ⚠️ **SHAPE MATCH** — `to_sql('whiskies')` with columns `['whisky_id','name','distillery_id','type','brand','region','age','age_statement','abv']` → no `data_confidence` column → inserted rows take schema default **NULL**. But it has a hard guard: `stop_import=True` when `existing_w_count>0` (line 111-116). At the time production already held 3,557+ rows → it would have **refused** the import. Medium confidence it was NOT the live writer (or ran before the guard was added). |
| 3 | `scripts/71_import_to_staging.py` | **NO by design** | Legacy staging DB seeder | Refuses prod | ❌ Explicitly aborts: `if "production.db" in db_path: sys.exit("CRITICAL ERROR: Refusing to run against production.db!")`. Targets `output/import/staging_test.db`. Ruled out. |
| 4 | `mr-kep/resolution/upsert_resolver.py` (UpsertResolver) | **YES** (line 23 `sqlite3.connect(self.db_path)`) | Incremental UPSERT into `whiskies` | Only if instantiated | ❌ Writes `data_confidence='certified'` (line 48) + id `gsd_candidate_id`. Observed rows are `NULL` + UUID/`W0` ids. Mismatch. Also: **zero callers** in the repo (`grep UpsertResolver` → only the class def). Dead code. |
| 5 | `backend/app/services/review_query_service.py` | **YES** (line 164 `sqlite3.connect(self._write_path)`) | Review-queue action log | Writes `review_actions` + staging tables only | ❌ `execute_action` (line 149) UPDATEs staging + INSERTs `review_actions`. Never touches `whiskies`. Mismatch. |
| 6 | `backend/app/providers/csv_provider.py` | **NO** | In-memory CSV→search items for the API | Never opens production.db | ❌ Read-only in-memory builder. Reference 1's "generated UUID inserts" claim is **wrong** — it only sets `external_id=f"csv-{uuid.uuid4().hex[:8]}"` on a Python object, never persists to the DB. |
| 7 | `backend/app/providers/sqlite_read_adapter.py` | **NO** (`?mode=ro`) | Read adapter | Read-only | ❌ |
| 8 | `backend/app/services/db_read_service.py` | **NO** (`?mode=ro`) | Read service | Read-only | ❌ |
| 9 | `backend/app/main.py` `@app.post("/api/whiskies/normalize")` | n/a | API normalize endpoint | Stateless transform, no DB write | ❌ |
| 10 | `backend/app/routers/admin_review.py` `@router.post("/action")` | delegates to #5 | Review action | Via #5 only | ❌ (see #5) |
| 11 | `scripts/p49_import_planner.py` | **NO** (text only) | Emits SQL as markdown | No `.commit()` | ❌ |
| 12 | `scripts/p50_import_executor.py` | writes **staging** DB | Promotion executor | "Production untouched" | ❌ |
| 13 | `scripts/p60_whiskybase/promote_staging.py` | writes `whiskies` (staging) | WhiskyBase promotion | `data_confidence='medium'`, W#### ids | ❌ Mismatch (NULL + UUID). |
| 14 | `scripts/p45_stage7_gate.py` | **NO** (`?mode=ro`) | Gate report | Read-only | ❌ |
| 15 | `scripts/external_sources/match_structured_whisky_source_to_production.py` | **NO** (`?mode=ro`) | Match preview | CSV out | ❌ |
| 16 | `scripts/external_sources/match_structured_ml_whiskey_source_to_production.py` | **YES** (line 63 `sqlite3.connect(db_file)` RW, **no `?mode=ro`**) | Structured-ML source fuzzy matcher | **No** — opens RW but only `SELECT … FROM whiskies` (line 64) then `conn.close()`; writes a CSV report only | ❌ Opens an ungated RW connection but issues **no INSERT/UPDATE**. Not the writer; still a latent ungated RW path. |

## Summary of real RW write paths to production.db
1. `etl/ingest_whisky_database.py` (writes `whisky_products`; connection ungated) — **not** the `whiskies` NULL writer
2. `scripts/72_production_import_seeder.py` (guarded by in-script `stop_import`; writes `whiskies`) — shape match, guarded out
3. `mr-kep/resolution/upsert_resolver.py` (dead code; would write `whiskies` with `certified`) — not the writer
4. `backend/app/services/review_query_service.py` (writes `review_actions`/staging)
5. `scripts/external_sources/match_structured_ml_whiskey_source_to_production.py` (opens ungated RW but **read-only in practice** — SELECT only)

Of these, only #2 has the correct *shape* (bulk `whiskies` append, NULL default) to have produced the `W00xxxx` NULL rows, but its own guard would have refused because rows already existed. **None of the repo scripts explains the 790 UUID/SMWS NULL rows** — that writer ran from outside the current tree (unidentified). All five RW connections are ungated and none routes through a P97/P98 promotion gate. See `architectural_gap_assessment.md`.
