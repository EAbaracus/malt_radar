# P404 — Real Apply Report (GO EXECUTED)

**Human GO received. Controlled promotion executed against `output/import/production.db` with the full gate satisfied: human GO + pre-apply backup + pre-apply SHA256 + lossless rollback snapshot retained.**

## Gate satisfied
- ✅ Human GO: explicit "go" from project owner
- ✅ Backup: `backups/production.pre_p404_book_promo.20260720_131614.db` (sha `3c56de60…`)
- ✅ Pre-apply SHA256 captured: `3c56de601c539260b49df57657eae4d47bfc8d0ebb27354b01c20648ac71656c`
- ✅ Lossless rollback snapshot retained: `rollback_snapshot_book_rows.json` (8 original book rows, incl. W000014/W002442 duplicates)

## Real Apply result (idempotent upsert)
| Metric | Value |
|---|---|
| Inserted | **58** |
| Updated | **8** (6 existing-row updates + 2 duplicate-collapses) |
| Skipped | 0 |
| Failed | **0** |
| Final book-source rows | **64** (exactly 1 per manifest whisky) |
| Duplicate (whisky_id, source='book') rows | **0** |
| Evidence total | 993 → **1,049** |

## Post-apply verification (live queries, not estimates)
- Book rows: **64**, distinct book whiskies: **64**, duplicate book rows: **0**
- 52 of the 64 are the whisky's **FIRST evidence** source
- Coverage: 20.87% → **22.09%**

## Idempotency (real 2nd pass on production)
- 0 inserted / 0 updated / **64 skipped** (no-op)
- Production DB SHA after rerun == after apply: `9c3e1ba7…` (unchanged by rerun)

## State transition
| Item | Before | After |
|---|---|---|
| production.db SHA256 | `3c56de60…` | `9c3e1ba7…` |
| flavor_evidence rows | 993 | 1,049 |
| book-source rows | 8 | 64 |
| duplicate book rows | (2 whiskies had 2 each) | 0 |

## Rollback readiness (lossless, still available)
If reversal is required: `DELETE` manifest book rows + re-INSERT the 8 original rows from `rollback_snapshot_book_rows.json` (original `evidence_id` + original values, including both W000014/W002442 duplicates). Simulated earlier and confirmed to restore exact original state.

## Verification
| Item | Value |
|---|---|
| git branch | `feature/editorial-crawl-phase` |
| git diff --stat | `source_priority.yaml` 4 lines (pre-existing CRLF artifact, unrelated to this promotion) |
| production.db SHA256 (post) | `9c3e1ba7d3e8911b50e9277ab175de774df0af696f8f4db815d7195b03db9b93` |
| knowledge.db SHA256 | `e4c0d8b4…` (unchanged) |

## Deliverables updated
- `_real_apply_state.json` (backup path + pre-apply SHA)
- `_real_apply_result.json` (real apply + idempotent rerun results)

**P403/P404 BOOKS PROMOTION: COMPLETE. 64 book-source evidence rows promoted idempotently with 0 failures and 0 duplicates; lossless rollback retained. No commit/push performed (per AGENTS.md, awaiting your instruction).**
