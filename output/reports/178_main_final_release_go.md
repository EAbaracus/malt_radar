# Malt Radar — Main Final Release GO

## Branch
main (HEAD: 910948d)

## Validation Date
2026-06-20 11:43 (UTC+3)

## Final Validation

| Gate | Result |
|------|--------|
| Backend tests (62 passed, 1 skipped) | PASS |
| Release gate (8/8) | PASS |
| Flutter analyze | PASS |
| Flutter DB API validation test | PASS |
| APK release build | SUCCESS |
| Android runtime smoke QA | PASS |

## APK Build

- Path: `frontend/build/app/outputs/flutter-apk/app-release.apk`
- Size: ~57.6 MB
- Build date: 2026-06-20 11:40

## Recent Commits (main)

```
910948d test: make API key security test pytest-compatible
9ce73fa merge: preserve local data when clearing cache
c9e6019 Merge pull request #9 from EAbaracus/security/backend-recheck-fixes
d69f97c chore: remove generated output artifacts from version control
8b805ed security: harden backend api key and sqlite read paths
```

## Security Hardening (10SEC-BACKEND)

- API key fallback (`mock-secret-key-123`) removed
- Backend endpoint protection added via `verify_api_key` dependency
- SQLite read path hardened (dynamic path resolution via env var)
- Table whitelist (`ALLOWED_TABLES`) added to prevent SQL injection
- `PRAGMA foreign_keys = ON` enforced on all SQLite connections
- Bare `except:` blocks replaced with specific exception handling
- Generated output artifacts removed from version control

## Critical Files

- `output/import/production.db`: unchanged
- `frontend/lib/core/config/app_config.dart`: unchanged (`useDbApi = false`)

## Final Decision

> **GO**

## Release Scope

| Scope | Decision |
|-------|----------|
| Beta / internal testing | GO |
| Production candidate | GO |

## Tag Önerisi (henüz atılmadı)

```bash
git tag -a v0.1.0-beta -m "Malt Radar beta release candidate"
git push origin v0.1.0-beta
```
