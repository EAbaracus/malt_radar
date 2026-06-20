# Cache Clear Persistence & Reference Delete Report (Stage 10H)

## Root Cause
Previously, `WhiskyRepositoryImpl.clearCache()` deleted rows from the main `whiskies` and `whiskyPrices` tables that did not have matching IDs in user favorites or scores. This is destructive for a persistent offline SQLite database, as it discards master whisky data that should remain stored persistently.

---

## Files Changed
- **`[NEW]`** [cache_clear_persistence_test.dart](file:///C:/Users/eltun/Documents/malt%20radar/frontend/test/cache_clear_persistence_test.dart) — Test suite verifying that `clearCache()` has no destructive effects on persistent data.
- **`[NEW]`** [reference_whisky_clear_test.dart](file:///C:/Users/eltun/Documents/malt%20radar/frontend/test/reference_whisky_clear_test.dart) — Test suite verifying that clearing the reference whisky only affects the configuration settings.
- **`[MODIFY]`** [whisky_repository.dart](file:///C:/Users/eltun/Documents/malt%20radar/frontend/lib/features/whisky/domain/repositories/whisky_repository.dart) — Added `Future<void> clearReferenceWhisky()` declaration.
- **`[MODIFY]`** [whisky_repository_impl.dart](file:///C:/Users/eltun/Documents/malt%20radar/frontend/lib/features/whisky/data/repositories/whisky_repository_impl.dart) — Refactored `clearCache()` to be a safe no-op. Implemented `clearReferenceWhisky()` to delete configurations.
- **`[MODIFY]`** [settings_screen.dart](file:///C:/Users/eltun/Documents/malt%20radar/frontend/lib/features/whisky/presentation/screens/settings_screen.dart) — Added confirmation dialog, a button to clear the reference, provider invalidation, and localized SnackBars.
- **`[MODIFY]`** [app_translations.dart](file:///C:/Users/eltun/Documents/malt%20radar/frontend/lib/core/localization/app_translations.dart) — Added localization translation keys for Turkish and English.

---

## clearCache Old Behavior
The old `clearCache()` fetched favorites and scores IDs, compiled a list of IDs to keep, and executed a delete statement against `whiskies` and `whiskyPrices` for any IDs not in the keep list:
```dart
await (_db.delete(_db.whiskies)..where((tbl) => tbl.id.isNotIn(keepIds.toList()))).go();
await (_db.delete(_db.whiskyPrices)..where((tbl) => tbl.whiskyId.isNotIn(keepIds.toList()))).go();
```

---

## clearCache New Behavior
The new `clearCache()` is a non-destructive no-op function:
```dart
@override
Future<void> clearCache() async {
  // The local whisky database is persistent offline app data, not disposable cache.
  // Do not delete whiskies, user lists, favorites, scores, notes, or settings here.
  return;
}
```

---

## Reference Delete Behavior
Added `clearReferenceWhisky()` to target settings:
```dart
@override
Future<void> clearReferenceWhisky() async {
  await (_db.delete(_db.userSettings)
        ..where((tbl) => tbl.key.isIn([
          'reference_whisky_id',
          'reference_whisky_absolute_score',
        ])))
      .go();
}
```
When triggered, providers are invalidated, updating the main layout to redirect the user back to the initial `SetupScreen` since no active reference remains.

---

## Tests Run
Targeted test execution results:
- `test/cache_clear_persistence_test.dart` — **PASS**
- `test/reference_whisky_clear_test.dart` — **PASS**
- `test/user_lists_schema_test.dart` — **PASS**
- `test/user_lists_repository_test.dart` — **PASS**
- `test/db_api_validation_test.dart` — **PASS**
- `test/real_csv_seed_test.dart` — **PASS**
- `test/db_seed_test.dart` — **PASS**
- `test/similar_flavor_test.dart` — **PASS**

All tests compiled and passed successfully without hanging timers.

---

## Repository Status
- **production.db changed:** **NO**
- **AppConfig.useDbApi=false:** **YES**

---

## GO/NO-GO
# **GO**
The cache clear persistence bug has been resolved with safe, non-destructive behavior. Reference whisky deletion is fully functional, complete with localized confirmation dialogs and comprehensive test coverage.
