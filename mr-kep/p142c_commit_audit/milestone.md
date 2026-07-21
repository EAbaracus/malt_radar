# P142C — Milestone

- doc_version: P142C-1
- milestone: SMWS metadata normalization & promotion pipeline complete (P139 → P142).

## What this milestone delivers
1. **P139** — Production metadata promotion executed via guarded NULL_FILL (628 fields:
   627 cask_type + 1 region). 530 region candidates deferred because they held `''`
   (non-NULL), not true NULL. Original preserved; rollback.sql generated.
2. **P140** — READ-ONLY audit proving the `''`-vs-NULL hypothesis: `region` (713) and
   `age_statement` (791) stored empty-string; 4 columns were 100% NULL → `''` is an anomaly.
   Recommendation: NORMALIZE_TO_NULL.
3. **P141** — Authorized `''` → NULL normalization: 1504 cells (region 713 + age_statement 791)
   converted in one transaction, 0 overwrites, integrity ok. Unlocked the 530 deferred rows.
4. **P142** — Authorized deferred region NULL_FILL: 530 region values promoted (conf 0.95, smws),
   0 overwrites, integrity ok. Region real-nonempty coverage 417 → 947 (+530).

## Net effect on production.db
- cask_type non-null: 54 → 681 (+627)
- region real-nonempty: 417 → 947 (+530, after P141 stripped 713 `''`)
- age_statement: `''` (791) → NULL (normalized, no promotion yet)
- 0 overwrites, 0 deletes/inserts, 0 UUID changes across all phases.

## Commit
- hash `5de4c42978c3450c9c796506d6be61fb63742699`, parent `6d8e9e2`.
- 28 documentation/artifact files, 8323 insertions. No `.db`, no `.bak`, no backup.
- Not pushed (per spec).

## Safety artifacts retained (untracked, outside commit)
- `mr-kep/p139_production_promotion/backups/production.db.pre_p139.*.bak`
- `mr-kep/p141_null_normalization/backups/production.db.pre_p141.*.bak`
- `mr-kep/p142_region_completion/backups/production.db.pre_p142.*.bak`
- `rollback.sql` per dir (text, reversible)

## Status
Milestone FROZEN and committed. Pipeline is complete, evidence-backed, reversible.
