# P251 — 06 — FINAL VERDICT

## Headline

The final apply plan (post-P250 MERGE_SAFE) is **simulation-verified across all three waves** and
is **safe to execute under an authorized, gated run** — with one critical caveat on Wave C. No
production write, merge, schema change, or commit was performed.

## Per-wave outcome

| Wave | Rows | FK | Identity | Evidence | Idempotent | Verdict |
|------|-----:|:--:|:--------:|:--------:|:----------:|---------|
| **A** AUTO_BIND | 1,902 | ✅ 0 violations, 215 valid targets | ✅ whisky_id/name/age/abv frozen | n/a (FK only) | ✅ 0 re-apply | **SAFE** |
| **B** D1091→D0010 | 5+5+5 repoint | ✅ →D0010 (Speyside) | ✅ whisky_id frozen | ✅ **0 lost** (0 FE, 5 FP, 5 TN preserved) | ✅ 0 re-apply | **SAFE** |
| **C** NFKC fold | 55 name hits | n/a | ⚠️ name column | n/a | ✅ | **PARTIAL — collision-gated** |

## Key validation results

- **FK integrity:** before 0, after-sim 0. ✅
- **Identity preservation:** `whisky_id` changed on **0** rows across all waves. ✅
- **Evidence preservation:** Wave B loses **0** evidence rows; all 15 child records carry to D0010. ✅
- **Idempotency:** every wave is a pure function of immutable inputs; re-apply net change = 0. ✅
- **NULL `distillery_id` before → after (Wave A):** 1,931 → 724. ✅

## The one caveat (Wave C)

NFKC name normalization creates **13 `whiskies`/tasting_notes within-table collisions** (e.g.
"glen scotia double cask", "ardbeg corryvreckan", "amrut peated" each appear on two distinct
rowids). These are **not duplicates** — they are different expressions that share a normalized
spelling. **Auto-applying Wave C to `whiskies`/`tasting_notes` would create false duplicate
identities.** Required controls:
1. Apply Wave C name-fold to **`distilleries.name` only** (safe; drives the merge).
2. For `whiskies`/`tasting_notes`, auto-apply **only the unique-normalized subset**; route the
   **13 colliding pairs to HUMAN_REVIEW** (disambiguate via `original_name`/age before any rename).

## Recommended execution order (future authorized task)

1. Snapshot + SHA gate.
2. Wave A (1,902 binds) → R4/FK gate.
3. Wave B (repoint 15 + deprecate D1091) → evidence check (expect 0 loss).
4. Wave C (distilleries.name fold + unique-only whisky names; colliding 13 → review).
5. Full rollback-ready via snapshot + audit trail.

## Validation (this audit)

- production.db SHA frozen == final:
  `f341995184e883232e6993aa77ca103e2531d464a95d449c15a6ce857bf67a12` ✅ **UNCHANGED**
- Opened exclusively read-only (`uri mode=ro`); no write connection; no `-wal`/`-journal` sidecar. ✅
- No UPDATE/MERGE/DELETE/INSERT executed; no schema change; no commit/push. ✅
- Only 6 report files + 2 helper `_*.json`/`_*.py` added under
  `mr-kep/p251_entity_binding_apply_preflight/`. ✅

**STOP after dry-run validation — no mutation performed.**
