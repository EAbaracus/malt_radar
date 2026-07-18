# P95B Phase 12 — Migration Report

**Authorization:** Human GO granted (P95B Phase 12 — Production Schema Migration & Promotion).
**Date:** 2026-07-18 · **Executor:** gated single-script `mr-kep/p95b_phase12/p95b_phase12_execute.py`.
**Rules honored:** exactly one transaction for schema migration; rollback-on-failure at every phase;
never overwrite T1/T2 authority; vector_rich retained as legacy; no unrelated refactoring.

---

## Phase A — Backup (PASS)
| Step | Result |
|---|---|
| production.db exists | ✅ |
| PRE-SHA256 | `8350fe9de2f1c73d9c4b6930bae607afe64696527910c2709b8b3a4a634c6a3a` |
| Timestamped backup | `mr-kep/p95b_phase12/backups/production.db.pre_p95b_phase12.20260718_101917.bak` |
| Backup SHA == PRE-SHA | ✅ (verified before proceeding) |

## Phase B — Schema Migration (PASS, single transaction)
- `ALTER TABLE flavor_evidence ADD COLUMN vector_maritime REAL;` — executed in one `BEGIN…COMMIT`.
- `vector_rich` **not removed** (retained as deprecated legacy evidence, per contract).
- On the first attempt a `NOT NULL source` constraint surfaced and Phase C rolled back; the
  half-applied ALTER was fully reverted from backup, the INSERTs corrected (added `source`),
  and the run was repeated cleanly.

## Phase C — Promotion (PASS, INSERT-only)
- **Book:** 8 validated rows (all 7 canonical axes complete + `whisky_id`) → 8 new `flavor_evidence` rows (`source='book'`).
- **Tasting notes:** 263 crosswalk-resolved (`matched_master_whisky_id` not null, not rejected) →
  188 promoted (`source='tasting_note'`), **75 skipped** (no canonical descriptor tokens extracted).
- **Total new evidence:** 196 (8 + 188). `flavor_profiles`: 0 new rows inserted — all 196
  `whisky_id`s already had a profile row, so INSERT was skipped → **no overwrite of existing
  authority** (T1/T2 preserved).
- `vector_rich` set NULL for all new rows (never fabricated); legacy `vector_rich` on the
  791 pre-existing rows is retained untouched.

## Phase D — Validation (PASS)
| Gate | Expected | Actual |
|---|---|---|
| migration committed | true | ✅ |
| `vector_maritime` exists | true | ✅ |
| evidence rows before → after | 791 → 987 | ✅ (+196) |
| `evidence_id` unique | count == distinct | ✅ [987, 987] |
| no NULL `whisky_id` promoted | 0 | ✅ 0 |
| promoted profiles with exactly 7 canonical axes | 0 bad | ✅ 0 (0 new profiles) |
| maritime preserved | >0 non-null | ✅ 196 non-null |
| `rich` absent from canonical output | not introduced | ✅ (only legacy 791 retained) |
| `PRAGMA integrity_check` | ok | ✅ ok |
| Regression (P95B-FIX-02, 7 tests) | pass | ✅ `7 passed` |

## Phase E — Audit
- **before-SHA:** `8350fe9d…` · **after-SHA:** `704fee10138560b18492557feb1bd97a4a8dac35256d5dbae57c6c5a607323a1`
- **rollback executed?** No (all gates passed).
- **promoted evidence:** 196 (8 book + 188 tasting).
- **skipped:** 75 (no canonical tokens; see `promotion_audit_log.json`).
- **rollback instructions:** see `promotion_report.md` §Rollback.

## Final Status
**PASS — Phase 12 completed successfully.**
