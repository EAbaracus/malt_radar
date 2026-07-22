# [DEPRECATED / RETIRED] Malt Radar Pipeline — Maintenance Guide (Pipeline v1, FROZEN)

**WARNING:** This maintenance guide describes the **Classic Pipeline (P32-P42)** which has been **RETIRED** per P500-A. The active canonical architecture is **MR-KEP** (domain pipeline) + **KEP Runtime** (safety/execution layer). All production mutations MUST go through the KEP Runtime `PromotionGate` (`promotion_engine.py`). Do not use any old scripts or processes described below.

---

For historical reference only, the classic maintenance guidelines were:

## 0. Integrity first
Always verify freeze before and after any operation:
```
python tmp/pipeline_guard.py
```
`FROZEN-INTACT` = all canonical artifacts + production.db unchanged since freeze. Any violation means something was regenerated or production was touched — investigate before proceeding.

---

## 1. Adding new books
New source reviews arrive in `data/staging/new_staging_reviews.csv` (the P36 intake format: `score, expression, abv, tasting_notes, reviewer, source_file, source_page`).

1. Append new rows to `data/staging/new_staging_reviews.csv` (do NOT modify historical rows).
2. Re-run **P36 intake only** against the staging DB (read-only on production business tables; writes only `staging_*`). Use the P36 logic in `tmp/p36_phase*.py` as the reference implementation.
3. Re-run **P37→P38→P39** to stage the new matches (each phase is deterministic and referenceable from `tmp/p37_phase*.py`, `tmp/p38_phase*.py`, `tmp/p39_phase*.py`).
4. After staging, re-run **P40 readiness audit** (`tmp/p40_audit.py`) — this is read-only and safe.
5. Rebuild the approval queue (**P41**) from the refreshed staging.
> Do not regenerate historical P32–P35 artifacts for a new book; those phases are frozen. A new book only flows through P36–P42.

## 2. Rerunning P32 only
P32 is the import-value assessment; its outputs live in `output/reports/p32_*`. Because the pipeline is frozen, **do not overwrite** the frozen P32 artifacts unless a deliberate, documented re-baseline is authorized. To re-run for a *new* assessment without disturbing the freeze:
- Run the P32 logic into a **separate scratch directory** (e.g. `tmp/p32_reassess/`), not `output/reports/`.
- Compare results; if a re-baseline is approved, update the manifest via `tmp/p43_build_manifest.py` and re-freeze with a new timestamp.

## 3. Recovering from a failed phase
- **Staging-write failure (P35/P39 during run):** restore the relevant backup from `output/import/backups/` (`production_p35_premerge_*` or `production_p39_prestaging_*`). These contain the pre-write `staging_*` state.
- **Controlled apply failure (P42):** the apply runs in one transaction; on any exception it calls `rollback()` and writes nothing. If a partial write is suspected, restore `production_p42_preapply_<ts>.db` (created only on `--confirm-production-apply`).
- After recovery, re-run `python tmp/pipeline_guard.py`. If production.db hash changed unexpectedly, restore the latest valid backup and re-freeze.

## 4. Rebuilding staging
`staging_tasting_notes` is the only writable production table. To rebuild it from scratch:
1. Take a timestamped backup (`cp output/import/production.db output/import/backups/production_rebuild_<ts>.db`).
2. Run P36→P37→P38→P39 in sequence (reference implementations in `tmp/`). Each writes only `staging_*`, never production business rows.
3. Validate with P39's validation checks (row conservation, no dup `matched_master_whisky_id`, all IDs in `whiskies`).
4. Re-run P40 readiness audit + P41 approval queue.

## 5. Rebuilding the approval queue
1. Ensure `staging_tasting_notes` is current.
2. Run the P41 builder (`tmp/p41_build.py`) → regenerates `output/p41/*` (queue + splits + packages). Read-only on production.
3. The human review state lives in `output/p42/review_decisions.json` — preserved across queue rebuilds; re-run `python tmp/p42_review.py export` to regenerate `approved_reviews.csv` from current decisions.

## 6. Production deployment (controlled apply)
Precondition: P41 queue reviewed, ≥1 row approved, readiness audit shows promotable rows.
```
# 1. human review
python tmp/p42_review.py approve <staging_note_id>     # per row
python tmp/p42_review.py export                         # -> approved_reviews.csv

# 2. DRY RUN (safe, no write)
python tmp/p42_apply.py
#    expect: [DRY RUN] ... Would insert: N rows; skip: M

# 3. REAL WRITE (explicit flag)
python tmp/p42_apply.py --confirm-production-apply
#    creates production_p42_preapply_<ts>.db, single transaction, dup-skip, FK check,
#    automatic rollback on failure, writes reports.
```
After apply: re-run `python tmp/pipeline_guard.py` to record the new production.db hash, then **re-freeze** by re-running `tmp/p43_build_manifest.py` and documenting the change with a new freeze timestamp. Never leave production in an undocumented post-apply state.

## 7. Rollback
- **Staging rollback:** restore `output/import/backups/production_p3X_*.db` (pre-staging-write) over `production.db`.
- **Production rollback:** restore `output/import/backups/production_p42_preapply_<ts>.db` over `production.db`.
- Both are full-file restores (simple, atomic, authoritative). No in-place edits.
- After any rollback, re-run the guard and re-freeze if hashes changed intentionally.

## Safety invariants (never violate)
- Production business tables (`tasting_notes`, `whiskies`, `flavor_profiles`, `distilleries`) are read-only except inside the single P42 apply transaction.
- No UPDATE/DELETE on production; INSERT only; single transaction; automatic rollback.
- No auto-approval; human sign-off mandatory.
- Do not regenerate P32–P42 canonical outputs except via a documented re-baseline + re-freeze.
- Stop and seek approval before any production deployment.
