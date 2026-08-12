# Anonim Okuma Katmanı (Anonymous Read Layer) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide an unauthenticated "Guest Mode" for the Malt Radar Flutter app by exposing a bounded allowlist of Tier A whiskies (N=150) through a dedicated public API namespace (`/api/db/public/*`) with SEO-parity response shaping, while retaining authenticated access for members.

**Architecture:** Build-time deterministic allowlist script (`scripts/build_anonymous_allowlist.py`) producing `artifacts/anonymous_allowlist.json`; a lightweight `AnonymousCatalogService` wrapping `ProductionReadAdapter` to intersect queries with allowlist IDs and apply 8-axis presentation shaping; a new `db_public_api.py` FastAPI router mounted at `/api/db/public`; and Flutter `DbWhiskyApiClient` adaptors with Guest UI navigation in `main.dart` and `auth_screen.dart`.

**Tech Stack:** Python 3.11, FastAPI, SlowAPI limiter, SQLite3 (read-only `ProductionReadAdapter`), Flutter (Dart / Riverpod).

## Global Constraints

- **Single Source of Truth:** `docs/superpowers/specs/2026-08-12-anonymous-read-layer-design.md` (Option 2 + Option A). Supersedes 2026-08-11 draft.
- **Read-Only DB Access:** Production DB (`output/import/production.db`) is read-only. All reads use `ProductionReadAdapter._get_connection()` (mode=ro). No SQL INSERT/UPDATE/DELETE.
- **Product Rule:** Fiyat kolonları (`production_price`, `price_value`, vb.) hiçbir kamu yanıtında bulunamaz.
- **Endpoint Boundary:** `/api/db/public/whiskies/{id}/evidence` ve `/api/db/public/whiskies/{id}/price-history` endpoint'leri public router'da tanımlanmaz (404). Authenticated `/api/db/*` router'ında üyeler için aktif kalır.
- **Backend Test Runner:** `cd backend && env -u PYTHONPATH .venv/Scripts/python.exe -m pytest tests/`
- **Frontend Test Runner:** `cd frontend && C:\Users\eltun\flutter\bin\flutter.bat test`
- **Human Approval for Commits:** Per AGENTS.md Rule 15, run `git commit` only when explicitly authorized by the user for each completed task.

---

### Task 1: Build-Time Allowlist Script & Determinism Verification

**Files:**
- Create/Modify: `scripts/build_anonymous_allowlist.py`
- Test: `backend/tests/test_allowlist_build.py`

**Interfaces:**
- Consumes: `seo.tiers.tier_map(conn)`, `ProductionReadAdapter`
- Produces: `artifacts/anonymous_allowlist.json` (`version`, `build_date`, `db_sha256`, `n`, `ids`)

- [ ] **Step 1: Write/verify failing tests for allowlist determinism & bounds**

```python
# backend/tests/test_allowlist_build.py
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
DB = ROOT / "output/import/production.db"

def _build(out: Path, limit: int = 50) -> dict:
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "build_anonymous_allowlist.py"),
         "--db", str(DB), "--out", str(out), "--limit", str(limit)],
        capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr
    return json.loads(out.read_text(encoding="utf-8"))

def test_allowlist_determinism():
    a, b = ROOT / "artifacts" / "_t1_a.json", ROOT / "artifacts" / "_t1_b.json"
    _build(a)
    _build(b)
    assert a.read_bytes() == b.read_bytes()
    a.unlink()
    b.unlink()

def test_allowlist_contained_in_tier_a_sitemap():
    out = ROOT / "artifacts" / "_t1_c.json"
    art = _build(out)
    import sqlite3
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    from seo.tiers import tier_map
    tiers = tier_map(conn)
    conn.close()
    assert all(tiers.get(wid) == "A" for wid in art["ids"])
    assert len(art["ids"]) == art["n"]
    out.unlink()

def test_allowlist_n_is_respected():
    out = ROOT / "artifacts" / "_t1_d.json"
    art = _build(out, limit=7)
    assert art["n"] == 7 and len(art["ids"]) == 7
    out.unlink()

def test_artifact_has_sha256_and_version():
    out = ROOT / "artifacts" / "_t1_e.json"
    art = _build(out)
    assert art["version"] == 1
    assert len(art["db_sha256"]) == 64
    out.unlink()
```

- [ ] **Step 2: Run test suite to verify script execution**

Run: `cd backend && env -u PYTHONPATH .venv/Scripts/python.exe -m pytest tests/test_allowlist_build.py -v`
Expected: PASS (script `scripts/build_anonymous_allowlist.py` is present and functional).

- [ ] **Step 3: Generate the official build artifact**

Run: `env -u PYTHONPATH .venv/Scripts/python.exe scripts/build_anonymous_allowlist.py --limit 150`
Expected: `allowlist: n=150 -> .../artifacts/anonymous_allowlist.json`

- [ ] **Step 4: Commit Task 1 after human approval**

```bash
git add scripts/build_anonymous_allowlist.py backend/tests/test_allowlist_build.py
git commit -m "feat(backend): add build-time anonymous allowlist script and tests (AL-A)"
```

---

### Task 2: AnonymousCatalogService (Bounded Intersect & SEO Response Shaping)

**Files:**
- Create: `backend/app/services/anonymous_catalog_service.py`
- Test: `backend/tests/test_anonymous_catalog_service.py`

**Interfaces:**
- Consumes: `artifacts/anonymous_allowlist.json`, `ProductionReadAdapter`, `DbReadService._normalize_flavor_profile`
- Produces: `AnonymousCatalogService.get_whiskies()`, `get_whisky()`, `get_flavor_profile()`, `search()`, `get_distilleries()`, `get_filters()`

- [ ] **Step 1: Write the failing tests for AnonymousCatalogService**

```python
# backend/tests/test_anonymous_catalog_service.py
import pytest
from app.services.anonymous_catalog_service import AnonymousCatalogService

def test_service_whiskies_bounded_to_allowlist():
    service = AnonymousCatalogService()
    res = service.get_whiskies(limit=100, offset=0)
    assert "items" in res
    assert len(res["items"]) <= 100
    allowlist = service.get_allowlist_ids()
    assert all(item["whisky_id"] in allowlist for item in res["items"])

def test_service_whisky_out_of_allowlist_returns_none():
    service = AnonymousCatalogService()
    result = service.get_whisky("NON_ALLOWLIST_ID_99999")
    assert result is None

def test_service_response_shaping_no_prices_no_raw_json():
    service = AnonymousCatalogService()
    res = service.get_whiskies(limit=5, offset=0)
    for item in res["items"]:
        assert "production_price" not in item
        assert "price_value" not in item
        assert "flavor_evidence" not in item

def test_service_offset_boundary_empty_list():
    service = AnonymousCatalogService()
    # offset past allowlist length
    res = service.get_whiskies(limit=50, offset=9999)
    assert res["items"] == []
    assert res["total_count"] == len(service.get_allowlist_ids())
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd backend && env -u PYTHONPATH .venv/Scripts/python.exe -m pytest tests/test_anonymous_catalog_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.anonymous_catalog_service'`.

- [ ] **Step 3: Implement AnonymousCatalogService**

```python
# backend/app/services/anonymous_catalog_service.py
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from app.db.production_read_adapter import ProductionReadAdapter
from app.services.db_read_service import DbReadService

ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_PATH = ROOT / "artifacts" / "anonymous_allowlist.json"

class AnonymousCatalogService:
    def __init__(self, artifact_path: Optional[Path] = None):
        self._adapter = ProductionReadAdapter()
        self._db_service = DbReadService()
        path = artifact_path or ARTIFACT_PATH
        if not path.exists():
            raise FileNotFoundError(f"Anonymous allowlist artifact missing: {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._allowlist_ids: List[str] = data.get("ids", [])
        self._allowlist_set = set(self._allowlist_ids)

    def get_allowlist_ids(self) -> List[str]:
        return self._allowlist_ids

    def get_whiskies(self, limit: int = 50, offset: int = 0, q: Optional[str] = None, filter: Optional[str] = None) -> Dict[str, Any]:
        offset = max(0, offset)
        limit = min(max(1, limit), 50)
        
        if offset >= len(self._allowlist_ids):
            return {"items": [], "total_count": len(self._allowlist_ids), "limit": limit, "offset": offset}
            
        sliced_ids = self._allowlist_ids[offset:offset + limit]
        
        with self._adapter._get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ",".join(["?"] * len(sliced_ids))
            query = f"""
                SELECT w.*, d.name as distillery_name, fp.flavor_profile as flavor_profile
                FROM whiskies w
                LEFT JOIN distilleries d ON w.distillery_id = d.distillery_id
                LEFT JOIN flavor_profiles fp ON w.whisky_id = fp.whisky_id
                WHERE w.whisky_id IN ({placeholders}) AND w.superseded_by IS NULL
            """
            params = list(sliced_ids)
            if q and len(q.strip()) >= 2:
                query += " AND w.name LIKE ?"
                params.append(f"%{q.strip()}%")
            
            query += " GROUP BY w.whisky_id ORDER BY w.name ASC"
            cursor.execute(query, params)
            rows = [self._shape_whisky(dict(row)) for row in cursor.fetchall()]

        return {
            "items": rows,
            "total_count": len(self._allowlist_ids),
            "limit": limit,
            "offset": offset,
        }

    def get_whisky(self, whisky_id: str) -> Optional[Dict[str, Any]]:
        if whisky_id not in self._allowlist_set:
            return None
        return self._db_service.get_whisky(whisky_id)

    def get_flavor_profile(self, whisky_id: str) -> Optional[Dict[str, Any]]:
        if whisky_id not in self._allowlist_set:
            return None
        return self._db_service.get_flavor_profile(whisky_id)

    def search(self, q: str) -> List[Dict[str, Any]]:
        raw_results = self._db_service.search(q)
        return [r for r in raw_results if r.get("whisky_id") in self._allowlist_set]

    def get_distilleries(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        return self._db_service.get_distilleries(limit, offset)

    def get_filters(self) -> Dict[str, Any]:
        return self._db_service.get_filters()

    def _shape_whisky(self, item: Dict[str, Any]) -> Dict[str, Any]:
        item.pop("production_price", None)
        item.pop("price_value", None)
        item.pop("price_context", None)
        item.pop("pour_size_ml", None)
        raw_fp = item.get("flavor_profile")
        if raw_fp:
            norm_json = DbReadService._normalize_flavor_profile(raw_fp)
            item["flavor_profile"] = json.loads(norm_json) if norm_json else None
        return item
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && env -u PYTHONPATH .venv/Scripts/python.exe -m pytest tests/test_anonymous_catalog_service.py -v`
Expected: PASS.

- [ ] **Step 5: Commit Task 2 after human approval**

```bash
git add backend/app/services/anonymous_catalog_service.py backend/tests/test_anonymous_catalog_service.py
git commit -m "feat(backend): implement AnonymousCatalogService with allowlist intersection and response shaping"
```

---

### Task 3: Public FastAPI Router `/api/db/public/*` & Cache Isolation

**Files:**
- Create: `backend/app/routers/db_public_api.py`
- Modify: `backend/app/main.py:28-32`
- Test: `backend/tests/test_db_public_api.py`

**Interfaces:**
- Consumes: `AnonymousCatalogService`
- Produces: Public FastAPI Router mounted at `/api/db/public` (`whiskies`, `whiskies/{id}`, `flavor-profile`, `search`, `distilleries`, `filters`)

- [ ] **Step 1: Write tests for `/api/db/public/*` endpoints & route isolation**

```python
# backend/tests/test_db_public_api.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_public_whiskies_unauthenticated_200():
    res = client.get("/api/db/public/whiskies")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert len(data["items"]) <= 150

def test_public_evidence_route_not_found_404():
    # Route does not exist in public router (G4 Option A isolation)
    res = client.get("/api/db/public/whiskies/GSD-CAND-0001/evidence")
    assert res.status_code == 404

def test_public_price_history_route_not_found_404():
    res = client.get("/api/db/public/whiskies/GSD-CAND-0001/price-history")
    assert res.status_code == 404

def test_authenticated_router_requires_auth():
    # /api/db/whiskies remains protected
    res = client.get("/api/db/whiskies")
    assert res.status_code == 401
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd backend && env -u PYTHONPATH .venv/Scripts/python.exe -m pytest tests/test_db_public_api.py -v`
Expected: FAIL (404 on `/api/db/public/whiskies`).

- [ ] **Step 3: Create router `backend/app/routers/db_public_api.py`**

```python
# backend/app/routers/db_public_api.py
from fastapi import APIRouter, HTTPException, Query, Request, Depends
from typing import Optional
from app.services.anonymous_catalog_service import AnonymousCatalogService
from app.security import limiter
from app.routers.db_api import check_db_api_enabled

router = APIRouter(
    prefix="/api/db/public",
    tags=["Public DB Catalog API"],
    dependencies=[Depends(check_db_api_enabled)]
)

def get_public_service() -> AnonymousCatalogService:
    return AnonymousCatalogService()

@router.get("/whiskies")
@limiter.limit("120/minute")
def get_whiskies(
    request: Request,
    limit: int = Query(50, ge=1, le=50),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None),
    filter: Optional[str] = Query(None),
    service: AnonymousCatalogService = Depends(get_public_service)
):
    return service.get_whiskies(limit, offset, q, filter)

@router.get("/whiskies/{whisky_id}")
@limiter.limit("120/minute")
def get_whisky(request: Request, whisky_id: str, service: AnonymousCatalogService = Depends(get_public_service)):
    result = service.get_whisky(whisky_id)
    if not result:
        raise HTTPException(status_code=404, detail="Whisky not found in public catalog")
    return result

@router.get("/whiskies/{whisky_id}/flavor-profile")
@limiter.limit("120/minute")
def get_flavor_profile(request: Request, whisky_id: str, service: AnonymousCatalogService = Depends(get_public_service)):
    result = service.get_flavor_profile(whisky_id)
    if not result:
        raise HTTPException(status_code=404, detail="Flavor profile not found in public catalog")
    return result

@router.get("/search")
@limiter.limit("120/minute")
def search(request: Request, q: str = Query(...), service: AnonymousCatalogService = Depends(get_public_service)):
    return service.search(q)

@router.get("/distilleries")
@limiter.limit("120/minute")
def get_distilleries(request: Request, limit: int = Query(50, ge=1, le=50), offset: int = Query(0, ge=0), service: AnonymousCatalogService = Depends(get_public_service)):
    return service.get_distilleries(limit, offset)

@router.get("/filters")
@limiter.limit("120/minute")
def get_filters(request: Request, service: AnonymousCatalogService = Depends(get_public_service)):
    return service.get_filters()
```

- [ ] **Step 4: Register `db_public_api.router` in `backend/app/main.py`**

```python
# backend/app/main.py
from app.routers import db_public_api  # Add import

app.include_router(admin_review.router)
app.include_router(db_api.router)
app.include_router(db_public_api.router) # Add line
```

- [ ] **Step 5: Run tests and full backend regression suite**

Run: `cd backend && env -u PYTHONPATH .venv/Scripts/python.exe -m pytest tests/test_db_public_api.py tests/test_db_api_auth.py -v`
Expected: PASS (Public routes 200 without auth; evidence/price-history 404 under `/public`; `/api/db/*` remains 401 without token).

- [ ] **Step 6: Commit Task 3 after human approval**

```bash
git add backend/app/routers/db_public_api.py backend/app/main.py backend/tests/test_db_public_api.py
git commit -m "feat(backend): mount /api/db/public router for unauthenticated catalog access"
```

---

### Task 4: Frontend Guest Navigation & Public API Adaptor

**Files:**
- Modify: `frontend/lib/core/api/db_whisky_api_client.dart`
- Modify: `frontend/lib/main.dart`
- Modify: `frontend/lib/features/auth/presentation/auth_screen.dart`
- Test: `frontend/test/guest_mode_navigation_test.dart`

**Interfaces:**
- Consumes: `/api/db/public/*` endpoints when `isGuest` is true.
- Produces: Guest mode entry path from AuthScreen ("Misafir Olarak İncele") to MainNavigationScreen.

- [ ] **Step 1: Write Widget test for Guest Mode button and navigation**

```dart
// frontend/test/guest_mode_navigation_test.dart
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:malt_radar/main.dart';
import 'package:malt_radar/features/auth/presentation/auth_screen.dart';

void main() {
  testWidgets('AuthScreen displays Guest Mode button', (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(home: AuthScreen()),
      ),
    );
    expect(find.text('Misafir Olarak İncele'), findsOneWidget);
  });
}
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd frontend && C:\Users\eltun\flutter\bin\flutter.bat test test/guest_mode_navigation_test.dart`
Expected: FAIL (text 'Misafir Olarak İncele' not found).

- [ ] **Step 3: Update `DbWhiskyApiClient` to support public base path when unauthenticated**

Modify `frontend/lib/core/api/db_whisky_api_client.dart` to prepend `/public` to URLs when `_token` is null:

```dart
String _basePath(String endpoint) {
  if (_token == null) {
    return '${AppConfig.baseUrl}/api/db/public$endpoint';
  }
  return '${AppConfig.baseUrl}/api/db$endpoint';
}
```

- [ ] **Step 4: Update `AuthScreen` with "Misafir Olarak İncele" button and update `main.dart` home router**

In `frontend/lib/features/auth/presentation/auth_screen.dart`, add TextButton:
```dart
TextButton(
  onPressed: () {
    ref.read(guestModeProvider.notifier).state = true;
  },
  child: const Text('Misafir Olarak İncele'),
)
```

In `frontend/lib/main.dart`, check `guestModeProvider` in `_mainHome`:
```dart
final isGuest = ref.watch(guestModeProvider);
if (!auth.isLoggedIn && !isGuest) {
  return const AuthScreen();
}
return const MainNavigationScreen();
```

- [ ] **Step 5: Run frontend test suite to verify Guest mode & regressions**

Run: `cd frontend && C:\Users\eltun\flutter\bin\flutter.bat test`
Expected: PASS.

- [ ] **Step 6: Commit Task 4 after human approval**

```bash
git add frontend/lib/core/api/db_whisky_api_client.dart frontend/lib/main.dart frontend/lib/features/auth/presentation/auth_screen.dart frontend/test/guest_mode_navigation_test.dart
git commit -m "feat(frontend): implement Guest Mode entry button and public API path routing"
```

---

## Verification & Final Review

After completing Tasks 1-4:
1. Run full backend pytest suite: `cd backend && env -u PYTHONPATH .venv/Scripts/python.exe -m pytest tests/`
2. Run full frontend flutter test suite: `cd frontend && C:\Users\eltun\flutter\bin\flutter.bat test`
3. Verify production DB SHA remains untouched.
4. Report completion to the user.
