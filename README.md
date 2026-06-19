# Malt Radar

Malt Radar is a Flutter-based whisky companion app with a whisky library, search, detail pages, scoring, flavor radar, similar flavor recommendations, personal notes, and price records.

## Current Status

* Android manual beta: READY
* Distribution method: Signed APK manual sharing
* Google Play: Deferred
* iOS / TestFlight: Deferred
* DB API: Behind feature flag and disabled by default
* Offline-first local database flow active
* Release candidate validated

## Features

* Whisky library
* Whisky search
* Whisky detail screen
* 100-point reference scoring
* Flavor radar chart
* Similar flavor recommendations
* Personal notes
* Price records
* English / Turkish localization
* First-launch locale policy:
  * Turkish device language → Turkish UI
  * Any non-Turkish device language → English UI

## Android Beta

APK path:
`dist/manual-apk-beta/MaltRadar-beta-release-2026-06-18.apk`

SHA256:
`7CED0E3C401B6FAD2A55B7ED0FC19EBF1C4777C6DA60113B88DDF938FC6D9F20`

Tester notes:
* Installing from unknown sources may be required.
* Testers should report the device model, Android version, screenshots/videos, and reproduction steps for any issue.

## Tech Stack

* Flutter / Dart
* Riverpod
* Drift / SQLite
* FastAPI backend
* Python ETL and testing tools
* Offline-first data seed flow

## Release Validation

The following gates passed:
* Signed release APK build
* Android manual smoke test
* Localization QA
* Setup screen overflow fix
* Flavor radar and similar flavor tests
* DB seed tests
* Security checks:
  * `key.properties` is not tracked
  * keystore / `.jks` files are not tracked
  * `production.db` was not modified
  * `AppConfig.useDbApi=false`

## Known Non-blocking Issues

* Some obsolete backend contract tests are classified as technical debt.
* `use_build_context_synchronously` analyzer info warnings remain.
* Tasting note / data content localization is deferred.
* Google Play and iOS distribution are deferred due to developer account costs.

## Roadmap

Phase 10+:
* Beta feedback triage
* Centralized user tasting notes
* Community-derived flavor profiles
* QR / barcode search
* Image / OCR search
* Premium feature gating
* Monetization / inline ads
* Data content localization
* Backend test cleanup

## Development

```powershell
cd frontend
flutter pub get
flutter analyze
flutter test test/db_api_validation_test.dart test/real_csv_seed_test.dart test/db_seed_test.dart test/similar_flavor_test.dart
flutter build apk --release
```

## Security Notes

* Do not commit `key.properties`.
* Do not commit `.jks` or `.keystore` files.
* Do not modify or promote `production.db` without explicit approval.
* Keep DB API disabled by default unless intentionally testing backend API mode.
