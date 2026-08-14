# Known Issues — Pre-existing Test Failures

These failures were present **before** the backend security hardening
(commit `ad49f8d` / `29460fb`) and are **not** caused by it. They are tracked
here for follow-up on the `fix/pre-existing-test-failures` branch.

## 1. `tests/test_seeder_script_fails_loudly`
- **Symptom:** `ModuleNotFoundError: No module named 'sqlalchemy'`
- **Root cause:** `scripts/72_production_import_seeder.py` imports `sqlalchemy`,
  but the active Python environment does not have it installed. The test runs
  the seeder as a subprocess and asserts a loud "CRITICAL ERROR: File not found"
  message, which never arrives because the process dies at import time.
- **Fix path:** Add `sqlalchemy` to the test/CI environment (or guard the import
  and assert the import-time failure is surfaced loudly), then re-run.

## 2. `tests/test_ingestion.py` (10 errors)
- **Symptom:** `sqlite3.OperationalError: no such table: source_audit`
- **Root cause:** The ingestion test fixture creates a test DB but the
  `source_audit` table is never created (the schema/migration setup step is
  missing or not invoked in the test harness). `etl/ingest_whisky_database.py`
  then fails on first insert.
- **Fix path:** Ensure the test DB is initialized with the full schema
  (including `source_audit`) before the ingestion tests run, matching what the
  production migration does.

## 3. `tests/test_editorial_promotion_writer.py` (6 errors)
- **Symptom:** `PermissionError: [Errno 13] Permission denied` on a temp
  `production_copy.db` under `pytest-of-eltun` (Windows).
- **Root cause:** The test copies `production.db` into a temp dir and the file
  handle/lock is not released before the next test reuses/removes it. This is
  Windows-specific file-locking behavior.
- **Fix path:** Close all connections explicitly and/or use `with` scoping for
  the temp DB copy; add a small retry/cleanup in teardown.

## Status
- All three are environment / test-harness issues, **not** regressions from the
  auth + SourceGuard work.
- The security-related suite (`tests/test_security_authz.py`,
  `tests/test_db_adapter_hardening.py`, `tests/test_db_read_api_smoke.py`,
  `tests/test_db_read_service_hardening.py`, `backend/tests/test_security_rechecks.py`)
  passes (113 passed, 1 skipped) on `main`.
