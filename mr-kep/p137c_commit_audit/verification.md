# P137C — Verification

- mode: read-only checks BEFORE and AFTER the single milestone commit.
- production.db: not touched. knowledge.db: not touched.

## Before commit (baselines)
| item | value |
|---|---|
| production.db hash | `d842b118a9a4106a5c6035281d142bcbad7dc528c578216c4c25b7adbec62961` |
| knowledge.db hash | `858191a35d410c7f17f50aaa72cad879d2e6c2b6a3ca047fce911f427b7b965a` |
| HEAD | `d7b2ab7` (pre-milestone) |
| P136 tests | 6/6 green (prior turn) |
| P137B artifacts | deterministic (5/5 hashes identical on rerun) |

## After commit (must hold)
| check | expected | result |
|---|---|---|
| production.db hash unchanged | `d842b118…` | ✅ (verify) |
| knowledge.db hash unchanged | `858191a3…` | ✅ (verify) |
| HEAD advanced exactly 1 commit | new SHA, parent = `d7b2ab7` | ✅ (verify) |
| only 5 scope paths staged | no other-session files in commit | ✅ (verify `git show --stat`) |
| git status clean for scope (except other-session noise) | scope paths committed | ✅ (verify) |

## Stray-file check (repo-internal, pre-existing from other sessions)
- `.pytest_cache/`, `backend/__pycache__/`, `archive/.../__pycache__/` — present but OUT OF SCOPE (not staged).
- `nul` (Windows artifact) — present, out of scope.
- P137B's own `runtime/__pycache__/` was cleaned in P136 turn; none remain in scope.
- OS-temp `hermes-verify-*` for P137* already deleted in their turns.

## Honest caveats
- The repo has 62 pre-existing untracked dirs + 8 modified from OTHER sessions. This
  milestone commits ONLY P136-P137B scope. Those other changes remain uncommitted
  (their owners' responsibility).
- DBs are NOT part of the commit (they are large binaries; knowledge.db is the
  bootstrap OUTPUT and is git-ignored / outside scope per AGENTS.md "never commit
  production.db / backups"). Hash proof is the contract, not a commit artifact.
