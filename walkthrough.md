# Backend Security Recheck Fixes (10SEC-BACKEND)

This walkthrough documents the security improvements and repo hygiene tasks completed during the 10SEC-BACKEND phase based on the `malt_radar_security_recheck.html` findings.

## Changes Made

### 1. API Route Protection (`main.py`)
- Removed the fallback `"mock-secret-key-123"` from the environment variable retrieval for `MALT_RADAR_API_KEY`.
- Introduced a `verify_api_key` dependency that explicitly rejects requests (HTTP 403) if the server's API key is not configured or if the incoming `X-API-Key` header is invalid.
- Applied this dependency to all public-facing API endpoints (`/api/whiskies/search`, `/api/whiskies/{id}`, `/api/whiskies/{id}/prices`, and `/api/whiskies/normalize`).

### 2. Seeder Script Hardening (`72_production_import_seeder.py`)
- **Strict Error Handling**: Removed silent `except:` blocks that previously fell back to empty DataFrames.
- The script now explicitly catches `FileNotFoundError` and broad `Exception`s, logs the error loudly using `print()`, and exits with code `1` (`sys.exit(1)`) if any critical CSV files are missing.
- Added a `sqlalchemy` event listener to enforce `PRAGMA foreign_keys=ON` immediately after connection creation.

### 3. Read Adapters & SQL Injection Prevention
#### `sqlite_read_adapter.py`
- Added an `ALLOWED_TABLES` whitelist corresponding to the known canonical tables.
- Table names are validated against this whitelist before string formatting in queries (e.g., `PRAGMA table_info({tname})` and `SELECT COUNT(*) FROM {tname}`).
- `PRAGMA foreign_keys = ON` is now enforced.

#### `db_read_service.py`
- Whitelisted tables via a `VALID_TABLES` set in `get_health()`.
- Enforced `PRAGMA foreign_keys = ON` upon connection.

### 4. Review Query Service (`review_query_service.py`)
- **Hardcoded Path Removal**: Refactored the `__init__` constructor to dynamically resolve the database path using `MALT_RADAR_DB_PATH` or fallback to `output/import/production.db` correctly.
- Created dual variables: `self._write_path` for absolute write paths and `self.db_path` for read-only URIs.
- Replaced the hardcoded path in `execute_action()` with `self._write_path`.
- Enforced `PRAGMA foreign_keys = ON` before executing `execute_action()`.
- **Exception Cleanup**: Replaced bare `except:` statements with specific exceptions (`sqlite3.OperationalError` and `sqlite3.Error`) and integrated Python's `logging` module to log queries that fail instead of failing silently.

### 5. Repository Hygiene
- Identified files intentionally tracked under `output/filestructure`, `output/reports`, and `output/review`.
- Executed `git rm --cached -r output/` to remove them from the index without deleting them from the disk.

### 6. Test Suite Updates
- **Added New Tests**: Created `tests/test_security_rechecks.py` to assert API key rejection on public routes, path injection logic in `ReviewQueryService`, strict file handling in the seeder, and table whitelisting in read adapters.
- **Fixed Legacy Tests**: Updated the old `test_db_adapter_hardening.py` and `test_db_read_service_hardening.py` to adapt to the new API Key requirements (mocking the API key in tests) and the removed deprecated schemas and health endpoints formatting.
- **All 62 tests are now passing.**

## Verification Results

✅ `pytest tests/ -v`: 62 passed, 1 skipped.  
✅ `git status --short`: `output/` files successfully untracked.  
✅ `git grep`: No raw bare `except:`, no `mock-secret-key-123`, and no hardcoded `production.db` remaining in connections.  
✅ `production.db` and `app_config.dart` remain unmodified as explicitly requested.
