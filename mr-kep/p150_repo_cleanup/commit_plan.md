# P150 — Commit Plan

- SAFE_TO_COMMIT: 72 paths (source edits/deletions + mr-kep reports/artifacts; verified NO *.db/*.bak present).
- KEEP_UNTRACKED: 2 paths (database/backup safety artifacts — NEVER commit).
- SHOULD_IGNORE: 3 paths (runtime leftovers — add to .gitignore).
- SHOULD_DELETE: 1 path (the `nul` garbage file).
- NEEDS_INVESTIGATION: 0 paths.

## Recommended commit grouping (optional, user decides)
1. **Core source changes**: `.github/workflows/android-release.yml`, `.gitignore`, `memory/current-phase.md`, and the `scripts/p53_flavor_verification/` deletions.
2. **Prior-session audit artifacts** (P103-P135): `mr-kep/p10*/`, `mr-kep/p11*`, `mr-kep/p12*`, `mr-kep/p13*` dirs.
3. **Current-session audits** (P138-P149): `mr-kep/p138_simulation/`, `mr-kep/p142c_commit_audit/`, `mr-kep/p143_release_readiness/`, `mr-kep/p144a_promotion_readiness/`, `mr-kep/p145_queue_reconciliation/`, `mr-kep/p149_commit_audit/`.
4. **Misc project artifacts**: `mr-kep/*.json`, `mr-kep/*.md`.

The exact `git add` commands below commit ALL SAFE_TO_COMMIT paths in one batch (per spec).
