# Malt Radar Data Pipeline — Overview (Pipeline v1, FROZEN)

**Status:** `PIPELINE_V1_FROZEN` · Freeze timestamp recorded in `output/release/pipeline_manifest.json`
**Scope:** P32 (import assessment) → P42 (human review & controlled apply). No new ETL phases.
**Golden rule:** Production business tables are read-only except inside a single controlled transaction authorized by a human. Writes only ever go to `staging_*` tables in `output/import/production.db`.

---

## Phase Diagram

```
 new_staging_reviews.csv ──┐
                            │
 P32  Import value assessment        (GO)
   └─> P33  Source extraction          (GO)
        └─> P34  Multiline parsing + quality  (NO-GO, quality-improve per P34.x)
             ├─> P34.5  Cross-page revalidation   (CANDIDATE)
             ├─> P34.6  Merge-readiness cleanup     (CANDIDATE)
             ├─> P35  Stage→DB merge               (GO)        [writes staging_* only]
             │
             ├─> P34A  Dataset builder (dup/divergent/missing) (GO)  [standalone freeze]
             │
 P35 ─> P36  New staging reviews intake   (PARTIAL GO: unmatched remain)
          └─> P37  Controlled review import (PARTIAL GO: conflicts held)
               └─> P38  Enrichment + manual resolution (PARTIAL GO: conflicts/unresolved)
                    └─> P39  Controlled staging apply  (PARTIAL GO: 263 staged, 240 held)
                         │
                         ├─> P40  Production readiness audit (NO GO: 0 promotable)
                         │       └─> P41  Approval workflow  (READY_FOR_HUMAN_REVIEW)
                         │                └─> P42  Human review + controlled apply (AWAITING_PRODUCTION_APPROVAL)
                         │                         └─[human --confirm-production-apply]--> production tasting_notes
                         │
                         └─> Pipeline v1 Freeze & Release (this doc set)
```

## Inputs
| Input | Path | Role |
|---|---|---|
| New staging reviews | `data/staging/new_staging_reviews.csv` | 1,108-row source for P36 intake |
| Production DB | `output/import/production.db` | master tables (`whiskies`, `tasting_notes`, `flavor_profiles`, `distilleries`) + `staging_tasting_notes` |
| P34 enriched staging | `data/staging/p34_*_enriched.csv` | P34 extraction products |
| P34.6 candidates | `data/staging/p34_6_*_p35_candidate.csv` | merge candidates for P35 |

## Outputs (canonical, frozen)
| Phase | Primary outputs (see manifest for full list + hashes) |
|---|---|
| P32 | `output/reports/p32_*` (assessment, preimport, gate) |
| P33 | `output/reports/p33_*` (extraction, data quality, gate) |
| P34 / P34.5 / P34.6 | `output/reports/p34*`, `data/staging/p34*_enriched.csv`, `data/staging/p34_6_*_candidate.csv` |
| P35 | `output/reports/p35_*` (merge, dry-run, post-validation, gate) — writes `staging_*` |
| P34A | `output/p34a/*` (duplicate candidates, divergent vectors, missing whisky, unresolved P32, gate) |
| P36 | `output/p36/*` (review inventory, matches, matched/unmatched/duplicate, validation, gate) |
| P37 | `output/p37/*` (audit, new/existing/conflicting, manual review, staging csv, validation, gate) |
| P38 | `output/p38/*` (enriched reviews, flavor tags, manual resolution, validation, gate) |
| P39 | `output/p39/*` (staging apply, validation, rollback, gate) — writes `staging_tasting_notes` |
| P40 | `output/p40/*` (readiness audit, promotion candidates/blockers, validation, rollback, gate) |
| P41 | `output/p41/*` (approval queue, ready/needs/already splits, checklist, statistics, summary, gate) |
| P42 | `output/p42/*` (approved/rejected, review audit, apply/validation/rollback reports, gate) |

## Gates (decision chain)
| Phase | Gate |
|---|---|
| P32 | GO |
| P33 | GO |
| P34 | NO-GO (quality-improve per P34.x) |
| P34.5 | CANDIDATE |
| P34.6 | CANDIDATE |
| P35 | GO |
| P34A | GO |
| P36 | PARTIAL GO (unmatched remain) |
| P37 | PARTIAL GO (conflicts held) |
| P38 | PARTIAL GO (conflicts/unresolved) |
| P39 | PARTIAL GO (240 held for manual) |
| P40 | NO GO (0 promotable rows) |
| P41 | READY_FOR_HUMAN_REVIEW |
| P42 | AWAITING_PRODUCTION_APPROVAL |

## Rollback Points
- **Before every staging write (P35, P39):** timestamped DB backup in `output/import/backups/` (`production_p35_premerge_*`, `production_p39_prestaging_*`). Restore = revert staging.
- **Before any production write (P42 apply):** `production_p42_preapply_<ts>.db` (created only on `--confirm-production-apply`). Restore = revert production.
- **P39 rollback proven:** backup restores `staging_tasting_notes` 733→470 pristine.
- **P42 rollback proven (temp-copy test):** transaction `rollback()` restores tasting_notes to pre-apply count.

## Approval Flow (P40 → P42)
1. **P40** — readiness audit classifies staging: READY_FOR_PROMOTION / PENDING_APPROVAL / ALREADY_IN_PRODUCTION / MISSING_DATA. (Result: 0 ready, NO GO.)
2. **P41** — builds `ready_for_review.csv` (372 HIGH). No auto-approval.
3. **P42 review tool** (`tmp/p42_review.py`): human `approve` / `reject` / `edit` → `review_decisions.json` (no production touch).
4. **P42 export** (`python tmp/p42_review.py export`) → `approved_reviews.csv`.
5. **P42 controlled apply** (`python tmp/p42_apply.py --confirm-production-apply`) — only with explicit flag.

## Production Flow (controlled apply)
```
human approve (tmp/p42_review.py approve <id>)
        │
        ▼
tmp/p42_review.py export  →  output/p42/approved_reviews.csv
        │
        ▼
tmp/p42_apply.py --confirm-production-apply
   1. backup production.db  (production_p42_preapply_<ts>.db, size-verified)
   2. BEGIN transaction
   3. INSERT only approved-and-NEW rows (skip dups, enforce FK to whiskies)
   4. COMMIT  (or rollback on any error)
   5. write production_apply_report.md / validation_report.md / rollback_report.md / gate_P42.md
```
**Production is currently UNCHANGED** (`tasting_notes` = 1848, `staging_tasting_notes` = 733). No apply has been run.

## Freeze & Integrity
- Manifest: `output/release/pipeline_manifest.json` (82 canonical artifacts, sha256 + mtime).
- Lock file: `output/release/PIPELINE_v1_FROZEN.lock`.
- Integrity check: `python tmp/pipeline_guard.py` — verifies all frozen hashes + production.db unchanged.
