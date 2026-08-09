# Frontend Legacy API Closure Implementation Plan

> **For Hermes:** Implement this plan task-by-task with TDD; commit (or hand to user) per task.

**Goal:** Remove the frontend legacy catalog path — `WhiskyRepositoryImpl` (concrete local-CSV repo),
`ApiClient` (the `/api/whiskies/*` HTTP client), and the `useDbApi == false` branch — so the catalog is
served **only** through `DbWhiskyRepositoryImpl` → `/api/db/*` (per-user bearer, the single source of
truth). This finishes the backend `/api/whiskies/*` closure (`50ffd15`).

**Architecture:** `DbWhiskyRepositoryImpl implements WhiskyRepository` is already a **full superset** of
all 12 abstract methods (20 `@override`), and its `searchExternalWhiskies` delegates to `searchBackend`
(Db client). Therefore legacy `WhiskyRepositoryImpl` + `ApiClient` are duplicate/dead classes. Remove
them, collapse `useDbApi` to constant-true, collapse the provider switch to always construct the Db repo.

**Tech Stack:** Flutter / Riverpod / Drift. Backend already is `/api/db`-only.

---

## Current state (verified in code, main = post-rebase `0fb2536`)

- `WhiskyRepositoryImpl` (`lib/features/whisky/data/repositories/whisky_repository_impl.dart`) — implements
  all 12 abstract methods; **network methods** (`searchExternalWhiskies`, `getWhiskyDetails`,
  `getWhiskyPrices`, `fetchAndUpdateDetails`) call `_apiClient` = `/api/whiskies/*` → **404 now**.
  **Local methods** (`watchLocalWhiskies`, favorites, personal notes, reference whisky, clearCache)
  are pure Drift reads/writes, still valid.
- `ApiClient` (`lib/core/api/api_client.dart`) — 3 calls are `/api/whiskies/{search,{id}/prices,{id}}`,
  all now 404. BUT `DbWhiskyApiClient` imports `ApiClient.baseUrl` static (`db_whisky_api_client.dart:34,43,52,...`)
  → **`ApiClient` cannot be deleted wholesale; `baseUrl` must move** to a shared location.
- `whisky_providers.dart` — `apiClientProvider` (→`ApiClient()`), `whiskyRepositoryProvider`
  switches on `AppConfig.useDbApi`: Db repo (true) vs legacy (`false`). `appInitializationProvider`
  seeds local DB only when `!useDbApi` (anti-scrape: web is force-true, so no seed needed there).
- `AppConfig.useDbApi` (`app_config.dart:23`) = `kIsWeb ? true : useDbApiConst`; `useDbApiConst`
  = `bool.fromEnvironment('MALT_RADAR_USE_DB_API', defaultValue: true)`. → effectively true everywhere.
- Tests `cache_clear_persistence_test.dart`, `reference_whisky_clear_test.dart`,
  `search_filter_test.dart` construct `WhiskyRepositoryImpl(db, ApiClient())` and exercise **only**
  local methods (`watchLocalWhiskies` with filters, cache/ref clear) — no `/api/whiskies` network call.

---

## Key decisions (please confirm)

1. **`ApiClient.baseUrl` move:** keep class but strip `/api/whiskies` methods, OR extract `baseUrl`
   into a small const (e.g. `ApiConfig.baseUrl`) and delete `ApiClient` entirely? Recommendation:
   **delete `ApiClient`, add `ApiConfig.baseUrl` const** used by `DbWhiskyApiClient`.
2. **3 tests that build the legacy concrete:** they test **local Drift** logic (not network). Options:
   a. Repoint them to `DbWhiskyRepositoryImpl` (it has the same local methods) — need a `DbWhiskyApiClient`
      instance; pass a stub/null (local methods won't touch it). (Recommended.)
   b. Move the local-method tests onto a pure Drift harness independent of the repository class.
   Recommend **(a)** — minimal churn, keeps behavior coverage.
3. **`useDbApi` constant-true collapse:** keep `AppConfig.useDbApi` getter returning `true` for
   minimal diff, or delete the flag entirely and inline backend-mode calls? Recommend **keep getter = true**
   (smallest, least risky) and delete only the `== false` branches + `useDbApiConst` fromEnvironment.
   This makes `--dart-define=MALT_RADAR_USE_DB_API=false` a no-op (documented).

---

## Tasks

### Task 1: Add `ApiConfig.baseUrl` const; delete legacy `ApiClient`'s `/api/whiskies` methods

**Objective:** Single shared API-base const; remove the 3 dying `/api/whiskies` methods.

**Files:**
- Create: `frontend/lib/core/api/api_config.dart`
- Modify: `frontend/lib/core/api/api_client.dart` (delete `/api/whiskies` methods), or delete whole file
- Modify: `frontend/lib/core/api/db_whisky_api_client.dart` (use `ApiConfig.baseUrl`)

**Step 1:** Create `api_config.dart`:
```dart
import 'package:flutter/foundation.dart';
class ApiConfig {
  static const String baseUrl = String.fromEnvironment(
    'MALT_RADAR_API_BASE_URL',
    defaultValue: 'http://localhost:8080',
  );
}
```
(Keep the exact `baseUrl` semantics currently in `ApiClient` — read it first.)

**Step 2:** `dart analyze lib/core/api` → must be clean.

**Step 3:** If deleting `ApiClient`, update `DbWhiskyApiClient` to use `ApiConfig.baseUrl` and delete
`api_client.dart`. Verify `dart analyze lib` → no unresolved `ApiClient` refs (only `_apiClient`
field in Db repo remains, which Task 3 removes).

### Task 2: Delete legacy `WhiskyRepositoryImpl` (concrete)

**Objective:** Remove the duplicate concrete class.

**Files:**
- Delete: `frontend/lib/features/whisky/data/repositories/whisky_repository_impl.dart`
- Modify: `frontend/lib/features/whisky/presentation/controllers/whisky_providers.dart`

**Step 1:** Remove import from `whisky_providers.dart`; delete the `else` branch returning
`WhiskyRepositoryImpl(db, client)`.

**Step 2:** `flutter analyze --no-pub` after rm-ing `ios/Flutter/ephemeral/Packages/.packages` →
only the 3 test references should remain.

### Task 3: Repoint the 3 local-method tests to `DbWhiskyRepositoryImpl`

**Objective:** Keep local-Drift coverage without the legacy concrete.

**Files:**
- Modify: `frontend/test/search_filter_test.dart`, `cache_clear_persistence_test.dart`,
  `reference_whisky_clear_test.dart`

**Step 1:** Replace `WhiskyRepositoryImpl(db, ApiClient())` with
`DbWhiskyRepositoryImpl(db, ApiClient(), DbWhiskyApiClient())` **only if the local methods are
deterministic without network**. If `watchLocalWhiskies`/`clearCache` in the Db impl drift from the
legacy logic, assert the same contracts pass.

**Step 2:** `flutter test test/search_filter_test.dart test/cache_clear_persistence_test.dart
test/reference_whisky_clear_test.dart --no-pub` → all green.

**Step 3:** If the Db impl's local methods differ semantically, instead extract the filters logic
into the test harness (option 2b) and document the drift.

### Task 4: Collapse `useDbApi` to constant-true; delete `== false` branches + seed gating

**Objective:** Single backend path; no runtime flag branch. Split the guard surface into two
classes verified by code:
- **(A) Dead-branch collapse** — `useDbApi && X` → `X`; `useDbApi ? a : b` (when a is the only live
  output) → `a`. Proven: `useDbApi` is constant-true today, so `&&` is a pure AND-fold and a
  ternary's true-dal is the only reachable side.
- **(B) Provider-fork preservation** — where `useDbApi && backendId != null` feeds a `? :` between
  a **backend provider and a LOCAL provider**, REMOVE `useDbApi &&` but KEEP the `backendId != null`
  fork. Proof needed (from verified code): `DetailScreen` is constructed without `backendId` at
  `list_detail_screen.dart:172`, `home_screen.dart:214`, `home_screen.dart:535`, and
  `Whisky.externalId` is nullable → `backendId == null` is REACHABLE at runtime, so the local
  provider dal is live, not dead.

**Files:**
- Modify: `frontend/lib/core/config/app_config.dart` (`useDbApi` → `true`; drop `useDbApiConst`)
- Modify: `frontend/lib/features/whisky/presentation/controllers/whisky_providers.dart`
  (`appInitializationProvider` drops the `!useDbApi` seed; `whiskyRepositoryProvider` always Db)
- Modify: `frontend/lib/features/whisky/presentation/screens/detail_screen.dart` (class A guards
  at `:56`,`:663`,`:668`,`:674`,`:677` collapse; class B fork at `:347` keeps `backendId != null`)
- Modify: `frontend/lib/features/flavor/presentation/widgets/similar_flavor_whiskies.dart`
  (class B fork at `:29` keeps `backendId != null`)

**Step 1:** Verify each guard's class before editing (read the surrounding code; if a `? :`
feeds a backend vs local provider, it's class B — keep the fork). Add a plan-task result table.

**Step 2:** set `useDbApi => true`; delete `useDbApiConst` + all `if (!AppConfig.useDbApi)`
branches. Run `flutter analyze --no-pub` → clean.

**Step 3:** For class A guards collapse `useDbApi && X` → `X`. For class B, remove `useDbApi &&`
only, leaving `backendId != null ? backendProvider : localProvider`.

**Step 4:** suite-green for class A and class B **as separate verifications** (per your
instruction): after class-A edits run the affected screen/widget tests; after class-B run them
again. Do NOT fold both into one commit — separate task commits, suite-green checked per commit.

**Step 5:** `flutter test test/ --no-pub` (excluding `widget_test.dart` first) → green.
**Step 6:** `flutter test test/widget_test.dart --no-pub` isolated → green.
**Step 7:** Commit — one commit for class-A collapse, one for class-B fork-preservation, per
suite-green gate.

---

## Verification

- `cd frontend && rm -rf build/unit_test_assets && chmod -R u+w ios/Flutter/ephemeral/Packages 2>/dev/null;
  rm -rf ios/Flutter/ephemeral/Packages/.packages`
- `flutter analyze --no-pub` → "No issues found!" (pre-existing unrelated unused-import warnings ok)
- `flutter test test/ --no-pub` → all passed (run `widget_test.dart` separately).
- Backend sanity (already green): `/api/whiskies/*` absent from `main.py` routes (only the comment).
- **No new dependencies.** No `assets:` CSV re-added (anti-scrape intact).

## Risks / open questions

- **`ApiClient.baseUrl` semantics** — must match the deployed `MALT_RADAR_API_BASE_URL` used by
  `DbWhiskyApiClient` today. Read `api_client.dart` first; do not silently change the default.
- **Test behavioral drift** — Task 3 asserts local-method contracts survive the swap. If the Db impl
  `watchLocalWhiskies` filters differ, extract rather than force.
- **`useDbApi` getter vs flag deletion** — keeping `getter => true` is the minimal-diff choice; fully
  deleting the flag is a larger refactor across `detail_screen.dart`/`similar_flavor` guards. Confirm
  which you want.

## Explicitly out of scope (do NOT do here)

- Backend changes (already closed in `50ffd15`).
- The brand rebrand PR #34 files (already merged on main).
- `strays-source` branch / connosr history / social stash management.

## Commit/push

AGENTS.md rule 15: no commit/push without explicit human instruction. Per-task commits staged;
final push only on your GO.
