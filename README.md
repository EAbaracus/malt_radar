# Malt Radar

Malt Radar is an offline-first whisky discovery and personal tasting companion app built with Flutter, local SQLite/Drift storage, and a guarded FastAPI backend layer.

The current beta focuses on stable local usage, whisky discovery, custom lists, flavor-based comparison, reference whisky setup, and safe Android beta distribution.

## Current Beta Status

**Status:** Beta candidate
**Android package:** `com.example.malt_radar`
**Current release tag:** `v0.1.0-beta`
**Default data mode:** Local/offline database
**DB API mode:** Disabled by default behind feature flags

The app is currently intended for manual APK beta testing before wider public distribution.

## Key Features

### Whisky Database

* Local whisky database bundled with the app.
* Search and browse whisky products.
* Whisky detail pages with tasting information, flavor data, and metadata.
* Offline-first behavior for stable beta testing.

### Reference Whisky Flow

* Users can select a reference whisky during setup.
* Reference whisky is used as a comparison anchor for later recommendations and scoring behavior.
* Users can remove the selected reference whisky from Settings and select a new one.

### Custom Lists

Built-in local user lists:

* Wishlist
* Favorites
* Tried
* Collection

Users can save whiskies into personal lists without requiring a backend account.

### Flavor Radar

Whiskies with flavor profile data can display a radar-style flavor chart.

Flavor comparison currently supports core flavor dimensions such as:

* Fruity
* Sweet
* Smoky
* Spicy
* Woody

### Similar Whiskies

The app supports flavor-based similar whisky recommendations.

Similarity is based primarily on flavor profile distance, with supporting metadata such as region/category used as secondary signals.

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
* Web support exists but Android beta is the primary current target

### Backend

* FastAPI
* Read-only database API layer
* API key protection
* SQLite read-path hardening
* DB path resolution via controlled configuration
* DB API feature flags

### Data Pipeline

The project includes Python scripts and tests for:

* Whisky database ingestion
* Distillery/product reconciliation
* Flavor gap candidate generation
* Dry-run import previews
* Safety checks before database changes

Production database writes are intentionally guarded and must not happen during normal beta builds.

## Important Safety Rules

The following files must not be modified accidentally:

* `output/import/production.db`
* `frontend/lib/core/config/app_config.dart`

Current beta default:

```dart
AppConfig.useDbApi = false
```

Generated/local files should not be committed:

* `dist/`
* Flutter build outputs
* APK files
* local rclone tokens/config
* temporary reports or generated artifacts unless explicitly intended

## Local Development

### Frontend Setup

```powershell
cd "C:\Users\eltun\Documents\malt radar\frontend"

flutter pub get
flutter analyze
flutter test
```

### Common Beta Test Command

```powershell
cd "C:\Users\eltun\Documents\malt radar\frontend"

flutter analyze

flutter test test/user_lists_schema_test.dart test/user_lists_repository_test.dart test/db_api_validation_test.dart test/real_csv_seed_test.dart test/db_seed_test.dart test/similar_flavor_test.dart test/cache_clear_persistence_test.dart test/reference_whisky_clear_test.dart test/tasting_notes_i18n_test.dart

flutter build apk --release --obfuscate --split-debug-info=build/symbols
```

### Backend Tests

```powershell
cd "C:\Users\eltun\Documents\malt radar"

$env:PYTHONPATH = "backend"

python -m pytest tests/ backend/tests/ -v

Remove-Item Env:\PYTHONPATH
```

## Android Beta Build

Generate an obfuscated release APK:

```powershell
cd "C:\Users\eltun\Documents\malt radar\frontend"

flutter build apk --release --obfuscate --split-debug-info=build/symbols
```

APK output:

```text
frontend/build/app/outputs/flutter-apk/app-release.apk
```

## Google Drive Beta Distribution

Beta APKs are distributed through a shared Google Drive folder:

```text
MaltRadar Beta
```

The upload script copies the latest APK, generates a SHA256 checksum, uploads it to Drive, and removes old versioned APKs.

Upload script:

```text
scripts/upload_beta_apk_to_drive.ps1
```

Run after a successful release build:

```powershell
cd "C:\Users\eltun\Documents\malt radar"

powershell -ExecutionPolicy Bypass -File scripts\upload_beta_apk_to_drive.ps1
```

Drive folder keeps:

* `MaltRadar-beta-latest.apk`
* `MaltRadar-beta-latest.apk.sha256.txt`
* the newest timestamped release APK
* install notes

Beta users should download:

```text
MaltRadar-beta-latest.apk
```

## Manual Android QA Checklist

Before sharing a new beta APK:

1. App opens successfully.
2. Whisky database loads.
3. Setup flow completes.
4. Reference whisky can be selected.
5. Settings > cache clear does not delete the whisky database.
6. Favorites and custom lists remain intact.
7. Reference whisky can be removed.
8. A new reference whisky can be selected.
9. Tasting notes respect selected language.
10. Flavor radar and similar whisky sections do not crash.
11. Release APK installs cleanly on emulator/device.

## Release Notes: v0.1.0-beta

Current beta includes:

* Android release hardening.
* Backend DB API security recheck fixes.
* Safe cache clear behavior.
* Reference whisky removal.
* Custom user lists.
* Tasting notes localization for English/Turkish UI.
* Google Drive APK upload workflow.
* Obfuscated Android release builds.

## Current Known Holds

The following work should remain separate from the current beta release unless explicitly merged:

* Similar flavor carousel UI refinement.
* Flavor import implementation preview.
* Additional tasting note dictionary expansion.
* Public store release workflow.
* Automated beta notification channel.
