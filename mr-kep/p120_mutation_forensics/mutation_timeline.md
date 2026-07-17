# Mutation Timeline — `production.db` (P120 Forensic)

_READ-ONLY reconstruction from DB row-counts, file mtimes, git state, and process
snapshots. All times local (repository host)._

## Row-count / size timeline

| timestamp | whisky count | delta | source of observation |
|---|---|---|---|
| 2026-07-09 13:47 | 3,293 | — | on-disk backup `production.db.p33_backup.20260709_134752` |
| (session start) | 3,557 | +264 | baseline stated at P103 audit start |
| 2026-07-15 20:21:52 | 3,876 | **+319** | `production.db` mtime; detected during P103 audit |
| 2026-07-15 21:08:03 | 3,959 | +83 | read-only check |
| 2026-07-15 21:17:54 | 4,749 | **+790** | fingerprint capture; mtime stable since |
| (final, 2× consecutive) | 4,749 | 0 | read-only re-checks — **stable** |

## Correlated events

| time | event |
|---|---|
| Jul-9 | Pre-existing curated import batch (`data_confidence='medium'`, 264 rows) already present |
| session start | P103 audit begins; all 4 audit scripts open DB `?mode=ro` |
| 20:07 | `audit_enrich.py` runs (read-only) |
| 20:21:52 | **External write burst #1 (+319, `data_confidence=NULL`)** — between audit scripts |
| 20:34 | `audit_fix_smws.py` runs (read-only) |
| 20:40 | 6 audit reports generated (universe=3,557 snapshot) |
| 21:08:03 | External write burst #2 (+83) |
| 21:08→21:17 | Forensic re-baseline pass (read-only) |
| 21:17:54 | External write burst #3 (+790); **writer stops** |
| post-21:17 | Repeated read-only checks: count steady at 4,749, no journal file → writer exited |

## Row composition (current, read-only)
- `data_confidence IS NULL` = 3,021
- `data_confidence = 'medium'` = 264 (the pre-session curated batch)
- other confidence values = 1,464 (Jul-9 baseline preserved)
- 3 existing rows had `region` enriched (W001798, W003023, W002238) — additive only

## Interpretation
Three discrete append bursts (319 / 83 / 790) over ~56 minutes, then silence.
Consistent with a **batch/bulk CSV import executed manually**, not a streaming
service (a service would produce steadier, smaller increments). The process has
since exited.
