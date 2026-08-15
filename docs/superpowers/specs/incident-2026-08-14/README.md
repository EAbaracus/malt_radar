# Incident 2026-08-14 — Production Write/Provenance Evidence

**Status:** RESOLVED — observation window restarted 2026-08-15
**Production writes:** allowed only via KEP PromotionGate / write_guard with human GO
**Baseline:** `cbffd16b…` historical; current `71744add…` under new observation

## Known facts

- Unauthorized/provisional closure commit: `2e46abd5c8cea920c5e966c45f9ca8555c34b8d2`
- Commit parent: `0bb9114e9b205bc93d8f3e0913e8e8e6498a3061`
- Observed production SHA at containment: `cbffd16b29433c983bb113b2e9a9f186dd94c1ff9dc6f5f1b13d97f084386177`
- Production target has `DEATHSTAR\eltun:(DENY)(WD,AD)` and `A R`.
- Production target has hardlink count `2`; twin: `C:\Users\eltun\Documents\.tmp.driveupload\320360`.
- The two production-targeting `malt-radar-auth-b2` uvicorn processes were stopped at `2026-08-14T07:16:11+0300`.
- No baseline update, production write, ACL change, or push was performed by the containment audit.

## First observation window (2026-08-14T18:45 UTC → 2026-08-15T09:45 UTC)

16 samples were collected. Samples 0–13 (14 consecutive hours) recorded SHA
`cbffd16b…` stable. Sample 14 (2026-08-15T08:45 UTC) recorded a SHA change to
`71744add…`.

### SHA change attribution — RESOLVED (legitimate PromotionGate write)

The sample-14 SHA change is **fully attributed to a legitimate, documented KEP
PromotionGate write**, not an unknown external writer:

| Field | Value |
|---|---|
| Commit | `cb9ffdc1c0c16e70c1a8b3b0318fe719f1cdd97f` |
| Message | `feat(kep): clean 29 synthetic flavor profiles via KEP PromotionGate write_guard` |
| Closure | `output/gate_synthetic_cleanup/synthetic_cleanup_closure.json` |
| Table | `flavor_profiles` (row count 4,409 unchanged; 29 synthetic profiles nullified) |
| Pre-SHA | `cbffd16b…` (matches incident containment SHA) |
| Post-SHA | `71744add…` (matches current live DB) |
| Rows updated | 29 |
| Integrity | `ok` |
| Backup | `output/gate_synthetic_cleanup/backups/production_2026-08-15T07-54-33.979218+00-00_pre_cleanup.db` |

Post-mutation stability: samples 14–15 (08:45, 09:45 UTC) both recorded
`71744add…`; subsequent live verification confirms the same SHA.

The observation contract is strict: any SHA change is a FAIL regardless of
attribution. Window 1 is recorded **FAIL (attributed)**. A new window is
restarted on the post-mutation SHA.

## Evidence files

- `identity_propagation_apply.py` — frozen byte copy of the untracked candidate implementation.
- `identity_propagation_dryrun.py` — frozen byte copy of the untracked candidate dry-run implementation.
- `evidence_hashes.txt` — SHA-256 of both frozen copies and source copies at capture time.
- `stability_observation.jsonl` — 16 samples from window 1 (append-only; window 2 appends after a fresh t=0 anchor).
- `stability_observation_archived_attempt.jsonl` — invalid first attempt (Temp path), excluded from both windows.
- `candidate_set_reconciliation.md` — country candidate 434→430 diff explained by five Faz-3 supersede updates.
- `stability_watcher.py` — read-only watcher implementation; never execute an apply script.

The frozen copies are evidence only. Do not execute them.

## Stability observation contract (window 2)

Window 2 starts at the post-mutation SHA `71744add…`.

- Window: **24 hours** minimum.
- Sampling: **once per hour**.
- Required samples: **25 samples** (`t=0` plus 24 hourly samples).
- Pass criterion: all 25 samples have the same byte SHA, logical fingerprint, row counts, journal state, and candidate-set hashes.
- Any SHA or logical fingerprint change is a FAIL and restarts attribution; no baseline update is allowed.
- Any candidate-set or logical-content change is a FAIL even if row counts remain constant.
- The watcher is read-only against production (`mode=ro`); its log is non-production evidence.

## Governance decision

`2e46abd5c8cea920c5e966c45f9ca8555c34b8d2` is recorded as an unauthorized/provisional closure-baseline commit made despite the active NO-GO decision. Its author metadata is generic and does not identify the originating session. This record is forward-only; no history rewrite is authorized.

`cbffd16b…` was never sealed as a trusted baseline. The current baseline candidate is `71744add…`, subject to window 2 passing.

## Stop condition

Do not run an apply, promotion, migration, baseline update, or Phase 2 work while a stability observation window is open unless the write is a documented KEP PromotionGate operation with its own pre/post SHA closure.
Do not push while an open incident prevents verification of the current baseline.
