# Possible Database Writers — `production.db` (P120 Forensic)

_READ-ONLY investigation. No database modified, no process killed, no commit._

## Method
Searched the entire repository for code paths that can write to `production.db`:
- `sqlite3.connect(` → 0 hits (repo uses `?mode=ro` or filename strings, not that literal)
- `production.db` / `output/import` references → 50+ Python files reference it
- `INSERT INTO | UPDATE ... SET | DELETE FROM` → ~90 Python files
- `.commit()` → ~50 Python files
- `DriftDatabase | drift` → 0 hits (no drift DB in repo)
- `*.dart` (Flutter) → 50 files (incl. `frontend/.../data_seed_service.dart`)

## Classification

### A. CURRENTLY RUNNING WRITER — NONE IDENTIFIED
No running process has a command line referencing `production.db`, `etl`,
`ingest`, `backend`, `scripts`, or the repo path. All running Python processes are
Hermes agent internals (see `runtime_process_analysis.md`). The writer process is
**not alive** at capture time (DB mtime stable, no journal file present).

### B. PLAUSIBLE LATENT WRITERS (in repo, CAN write, NOT running now)
| candidate | writes to | evidence | running? |
|---|---|---|---|
| `etl/ingest_whisky_database.py` | production (CSV→whiskies/distilleries) | `INSERT INTO whiskies`-class tables; requires `--db` arg | NO (no matching PID) |
| `scripts/72_production_import_seeder.py` | production seed | name + `output/import` reference | NO |
| `scripts/71_import_to_staging.py` | staging→prod | `output/import` reference | NO |
| `scripts/apply/apply_*.py` (~20 files) | production/staging candidates | `output/import` reference; many `.commit()` | NO |
| `scripts/tasting_notes/promote_uploaded_staging_notes_to_production.py` | production | `output/import` reference | NO |
| `frontend/lib/core/database/data_seed_service.dart` | production (Flutter seed) | seed service; **no dart/flutter process running** | NO |
| `backend/app/services/review_query_service.py` | production (review) | `production.db` reference | NO (no :8080 listener) |
| `mr-kep/book_enrichment_sprint0X/*.py` | knowledge.db (+ opens prod RO for lexicon) | grep listed them for `production.db` ref | NO |

### C. RULED OUT
- **P120 / P103 audit scripts** (`mr-kep/p103_corpus_audit/*.py`): all open
  `production.db` with `?mode=ro`; grep for `INSERT/UPDATE/DELETE/DROP/commit()`
  returns nothing but prose in a report. Verified read-only.
- **Git**: `output/` is gitignored (`.gitignore:42`); no commit touched the DB.
- **Hermes agent processes** (`hermes_cli.main serve`, `tui_gateway.slash_worker`,
  `moa_proxy.py`): no `production.db` reference; serve/worker only.
- **GOG Galaxy / Epic Games Launcher Python**: unrelated game launchers.

## Most likely writer (unconfirmed identity)
A **deterministic bulk CSV→production importer** in class B (most consistent with
`etl/ingest_whisky_database.py` or `scripts/72_production_import_seeder.py`), run
interactively between 20:21 and 21:17. Identity could not be captured because the
process exited before observation and the DB contains no self-logging of the import
(`source_audit` table exists but was not populated by the observed writes).
