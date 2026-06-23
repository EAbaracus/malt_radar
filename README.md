# Malt Radar

Malt Radar is an offline-first whisky discovery and personal tasting companion app built with Flutter, local SQLite/Drift storage, and a guarded FastAPI backend layer.

The current beta focuses on stable local usage, whisky discovery, custom lists, flavor-based comparison, reference whisky setup, and safe Android beta distribution.

## Current Beta Status

**Status:** Beta candidate
**Android package:** `com.example.malt_radar`
**Current release tag:** `v0.1.0-beta`
**Default data mode:** Local/offline database
**DB API mode:** Disabled by default behind feature flags

*Stitch premium UI milestone completed!*

The app is currently intended for manual APK beta testing before wider public distribution. "Production-ready" label is withheld until external data pipelines and database encryption are complete.

## Key Features & Screens

### Premium UI

* Premium dark “Obsidian & Amber” UI theme.
* Polished Home, Search, Detail, Radar, Lists, and Settings layouts.
* Beautiful empty states for Wishlist, Collection, and other custom lists.

### Whisky Database & Search

* Local whisky database bundled with the app.
* Search and browse whisky products.
* Whisky detail pages with tasting information, flavor data, and metadata.
* Offline-first behavior for stable beta testing.

### Reference Whisky Flow

* Users can select a reference whisky during setup.
* Reference whisky is used as a comparison anchor for later recommendations and scoring behavior.
* Users can remove the selected reference whisky from Settings and select a new one.

### Custom Lists (Wishlist / Collection)

Built-in local user lists:

* Wishlist
* Favorites
* Tried
* Collection

Users can save whiskies into personal lists without requiring a backend account. Empty states are gracefully handled with premium UI illustrations.

### Flavor Radar

Whiskies with flavor profile data can display a radar-style flavor chart.

Flavor comparison currently supports core flavor dimensions such as:

* Fruity
* Sweet
* Smoky
* Spicy
* Woody

### Similar Whiskies Navigation

The app supports flavor-based similar whisky recommendations natively on the detail screen.
Similarity is based primarily on flavor profile distance. Users can directly navigate through similar whiskies via premium horizontal carousel cards.

### Tasting Notes Localization

Tasting note labels and common Turkish tasting note phrases are localized at the presentation layer.

Example behavior:

* Turkish locale: `Burun`, `Damak`, `Bitiş`
* English locale: `Nose`, `Palate`, `Finish`

Raw database content is not overwritten. Unknown phrases fall back safely to the original text.

### Safe Cache Clearing

Cache clearing no longer deletes the local whisky database.

Protected local data includes:

* Whisky database rows
* User scores
* Favorites
* Custom lists
* Reference whisky settings unless explicitly removed by the user

## Architecture

### Frontend

* Flutter / Dart
* Drift SQLite
* Riverpod
* Local-first app state
* Android release build support

### Backend & Data Pipeline

* FastAPI (Read-only database API layer)
* SQLite read-path hardening
* DB API feature flags
* Python scripts for database ingestion, reconciliation, and flavor generation

## Important Safety & Security Rules

The following files must not be modified accidentally:

* `output/import/production.db` (Included but controlled)
* `frontend/lib/core/config/app_config.dart`

Current security / beta notes:

* Backend/API feature flag is disabled by default (`AppConfig.useDbApi = false`).
* Release HTTP hardening is applied.
* SQLCipher (local database encryption) is not yet implemented (planned).

## Validation & Quality

Current validation status:

* `flutter analyze` PASS
* `db_api_validation_test` PASS
* Release APK build PASS

## Local Development

### Frontend Setup

```powershell
# From the repository root
cd frontend
flutter pub get
flutter analyze
flutter test
```

### Common Beta Test Command

```powershell
# From the repository root
cd frontend
flutter analyze

flutter test test/user_lists_schema_test.dart test/user_lists_repository_test.dart test/db_api_validation_test.dart test/real_csv_seed_test.dart test/db_seed_test.dart test/similar_flavor_test.dart test/cache_clear_persistence_test.dart test/reference_whisky_clear_test.dart test/tasting_notes_i18n_test.dart

flutter build apk --release --obfuscate --split-debug-info=build/symbols
```

### Backend Tests

```powershell
# From the repository root
$env:PYTHONPATH = "backend"

python -m pytest tests/ backend/tests/ -v

Remove-Item Env:\PYTHONPATH
```

## Android Beta Build

Generate an obfuscated release APK:

```powershell
# From the repository root
cd frontend
flutter build apk --release --obfuscate --split-debug-info=build/symbols
```

APK output is stored locally at: `frontend/build/app/outputs/flutter-apk/app-release.apk`

## Google Drive Beta Distribution

Beta APKs are distributed through a shared Google Drive folder: `MaltRadar Beta`

The upload script copies the latest APK, generates a SHA256 checksum, uploads it to Drive, and removes old versioned APKs.

Upload script: `scripts/upload_beta_apk_to_drive.ps1`

Run after a successful release build:

```powershell
# From the repository root
powershell -ExecutionPolicy Bypass -File scripts\upload_beta_apk_to_drive.ps1
```

## Known Limitations & Holds

* This is a beta build, not production-ready.
* Local database encryption (SQLCipher) is not yet implemented.
* External tasting data pipeline is still staged/controlled.
* LYX/import scripts are not part of this UI release.
* Public store release workflow is pending.
* Automated beta notification channel is pending.
