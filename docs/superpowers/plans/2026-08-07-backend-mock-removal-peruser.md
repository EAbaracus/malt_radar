# Backend Mock/External Provider Removal + Single-Source Catalog — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the hardcoded mock providers (`WhiskyHunterProvider`, `WhiskyEditionProvider`) and the live distiller.com scraper (`DistillerProvider`) so `/api/whiskies/search` serves **only** the local CSV source. This enforces the product rule (no scraped third-party whisky data surfaced) and keeps the catalog data provenance local/backed.

**Architecture:** The `/api/whiskies/search` endpoint iterates `provider_instances = [CsvWhiskyProvider, WhiskyHunterProvider, WhiskyEditionProvider, DistillerProvider]` and short-circuits after CSV results. Removing the three non-CSV providers leaves a single-source path. `provider_map` (prefix→provider) shrinks to `{"csv": ...}`; external-id lookups for `wh`/`we`/`ds` prefixes become 400 "invalid external ID format".

**Tech Stack:** Python 3.11 · FastAPI · httpx (no longer used after Distiller removal) · BeautifulSoup (no longer used) · pytest

## Global Constraints

- Production.db is NEVER written; read-only copies only. This change touches no database file.
- The product rule: no scraped third-party whisky data is surfaced in the UI. Mock provider data violates this intent → removal is a compliance cleanup, not a feature.
- Do NOT stage unrelated pre-existing modified files (auth, android, frontend screens, etc.) — only the provider-removal files.
- Keep `CsvWhiskyProvider` + its `data/whisky_database_merged_max.csv` path intact (that is the local canonical source).
- Backend tests must run via `env -u PYTHONPATH .venv/Scripts/python.exe -m pytest tests/` (host PYTHONPATH breaks Hermes's venv for `pydantic_core`).

---

## Task 1: Remove mock + external provider classes from the codebase

**Objective:** Delete `WhiskyHunterProvider`/`WhiskyEditionProvider` from `mock_providers.py` and delete `distiller_provider.py`, then strip stale deps/imports.

**Files:**
- Modify: `backend/app/providers/mock_providers.py` (remove `WhiskyHunterProvider` + `WhiskyEditionProvider`; keep `BaseMockProvider` only if no other class uses it — see Step 1)
- Delete: `backend/app/providers/distiller_provider.py`

**Interfaces:**
- Produces: no more `WhiskyHunterProvider`, `WhiskyEditionProvider`, `DistillerProvider` anywhere.
- Consumes: `WhiskyProvider` base (unchanged) from `app.providers.base`.

- [ ] **Step 1: Inspect `mock_providers.py` for other classes**
  Read `backend/app/providers/mock_providers.py` in full. Determine: does `BaseMockProvider` (or anything else in the file) get used by any remaining class after removing `WhiskyHunterProvider`+`WhiskyEditionProvider`? If `BaseMockProvider` becomes dead, remove it too. If another class in the file still needs it, keep it.
  Report the exact final class list of the file.

- [ ] **Step 2: Delete the two provider classes**
  Rewrite `backend/app/providers/mock_providers.py` so it no longer contains `WhiskyHunterProvider` or `WhiskyEditionProvider`. If the file becomes empty, `git rm` it instead.
  Also `git rm backend/app/providers/distiller_provider.py` (the live distiller.com scraper).

- [ ] **Step 3: Check for dangling imports**
  `grep -rn "WhiskyHunterProvider\|WhiskyEditionProvider\|DistillerProvider\|distiller_provider\|mock_providers" backend/app backend/tests tests` — confirm the ONLY references now are ones you are about to fix in Task 2 (main.py imports/instances). No test files reference them (already verified: grep returned none).

- [ ] **Step 4: Prune now-unused deps in requirements (if verified unused)**
  Confirm `httpx` and `beautifulsoup4` are not used anywhere else in `backend/app`:
  `grep -rn "httpx\|BeautifulSoup\|from bs4" backend/app --include="*.py"`
  If they appear ONLY in distiller_provider.py (being deleted), remove them from `backend/requirements.txt`. If used elsewhere, keep them.

- [ ] **Step 5: Commit**
  ```bash
  git add backend/app/providers/ backend/requirements.txt
  git commit -m "refactor(backend): remove mock + external (distiller) whisky providers; single CSV source"
  ```
  (Commit only these files/delated ones; if `requirements.txt` unchanged in content, do not stage it.)

---

## Task 2: Rewire `/api/whiskies/search` + `provider_map` to CSV-only

**Objective:** `provider_instances` and `provider_map` collapse to the single CSV provider; external-id lookups for removed prefixes return a clean 400.

**Files:**
- Modify: `backend/app/main.py:99-112` (`provider_instances`, `provider_map`) and the import block lines 14-16.

**Interfaces:**
- Consumes: `CsvWhiskyProvider` (unchanged).
- Produces: `provider_map = {"csv": <csv_provider>}`; `get_provider()` returns None for any non-`csv` prefix → 400.

- [ ] **Step 1: Update imports**
  Remove lines 15-16:
  ```python
  from app.providers.mock_providers import WhiskyHunterProvider, WhiskyEditionProvider
  from app.providers.distiller_provider import DistillerProvider
  ```
  Keep `from app.providers.csv_provider import CsvWhiskyProvider` (line 14).

- [ ] **Step 2: Collapse provider_instances + provider_map**
  Replace lines 99-112 with:
  ```python
  # Single local source: the certified CSV catalog. (Mock + external providers
  # removed: surfaced only scraped/invented third-party data, violating the
  # product rule and adding surface. Catalog provenance is now local-only.)
  csv_provider = CsvWhiskyProvider(csv_paths=["data/whisky_database_merged_max.csv"])
  provider_instances = [csv_provider]
  provider_map = {"csv": csv_provider}
  ```

- [ ] **Step 3: Confirm search loop still short-circuits fine**
  The loop at lines ~166-175 iterates `provider_instances` (now a single CSV provider) and breaks after the CSV provider yields results. No change needed to the loop body — but verify by reading it that the `isinstance(provider, CsvWhiskyProvider): break` line still works with a single provider (it does).

- [ ] **Step 4: Verify external-id lookups for removed prefixes → 400**
  `get_provider()` opens `prefix = external_id.split("-")[0]` and returns `provider_map.get(prefix)` → now `None` for `wh-`/`we-`/`ds-`, so `get_whisky_details` raises 400 "Invalid external ID format". Confirm this is the intended behavior (yes).

- [ ] **Step 5: Run the backend test suite**
  ```bash
  cd backend && env -u PYTHONPATH .venv/Scripts/python.exe -m pytest tests/ -q
  ```
  Expected: all pass (previously 25 passed, 1 skipped). If any test asserted distiller/mock behavior, update/fix that test to CSV-only (report it).

- [ ] **Step 6: Commit**
  ```bash
  git add backend/app/main.py
  git commit -m "refactor(backend): /api/whiskies/search + provider_map now CSV-only (single local source)"
  ```

---

## Task 3: Update deployment docs / env (gate the surface)

**Objective:** Keep `DB_API_ENABLED=false` (already the deploy state) and document that `/api/whiskies/search` is CSV-only so the external data surface is closed in writing.

**Files:**
- Modify: `deploy/.env.example` (confirm `DB_API_ENABLED=false`; no code change needed if already false)
- Modify: `docs/deployment-live-status.md` (add one line: catalog sources are local CSV `/api/db` + `/api/whiskies/search` CSV-only; no external provider surface)

- [ ] **Step 1: Confirm `DB_API_ENABLED=false` in `.env.example`**
  `grep -n DB_API_ENABLED deploy/.env.example` — expect `DB_API_ENABLED=false`. If anything else, set to `false` (but do not commit a real key).

- [ ] **Step 2: Note the closed external surface in live-status doc**
  Append to `docs/deployment-live-status.md`: "Catalog sources now local-only: /api/db (backend/data, gated off for public web) + /api/whiskies/search is CSV-only. Mock + distiller providers removed (no third-party scraped data surface)."

- [ ] **Step 3: Run backend suite once more (regression) + commit**
  ```bash
  cd backend && env -u PYTHONPATH .venv/Scripts/python.exe -m pytest tests/ -q
  ```
  ```bash
  git add deploy/.env.example docs/deployment-live-status.md
  git commit -m "docs(deploy): catalog sources local-only; external provider surface closed"
  ```

## Self-Review

- **Spec coverage:** (a) remove mock providers → Task 1; (b) remove Distiller external scraper → Task 1; (c) `/api/whiskies/search` CSV-only → Task 2; (d) external-id prefix 400 → Task 2 Step 4; (e) docs/env → Task 3. All covered.
- **Placeholder scan:** every task has exact file paths (`app/providers/mock_providers.py`, `app/providers/distiller_provider.py`, `app/main.py:99-112`, `backend/requirements.txt`), exact commands, expected outputs. No TBD.
- **Type consistency:** `provider_instances` stays `List[WhiskyProvider]`; `provider_map` stays `Dict[str, WhiskyProvider]` but collapses to `{"csv": csv_provider}` — `get_provider()` and the search loop contract unchanged. No cross-task signature drift.
- **Open risk:** if a backend test asserts distiller/mock behavior is present, Task 2 Step 5 surfaces it and the plan instructs fixing that test to CSV-only (do not leave a test that requires a provider the code no longer wires).
