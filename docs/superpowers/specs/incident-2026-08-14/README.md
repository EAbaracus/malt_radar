# Incident 2026-08-14 — Production Write/Provenance Evidence

**Status:** ACTIVE INCIDENT / CONTAINMENT IN EFFECT
**Production writes:** forbidden pending explicit reauthorization
**Baseline:** `cbffd16b…` remains PROVISIONAL / UNTRUSTED

## Known facts

- Unauthorized/provisional closure commit: `2e46abd5c8cea920c5e966c45f9ca8555c34b8d2`
- Commit parent: `0bb9114e9b205bc93d8f3e0913e8e8e6498a3061`
- Current observed production SHA at containment: `cbffd16b29433c983bb113b2e9a9f186dd94c1ff9dc6f5f1b13d97f084386177`
- Production target has `DEATHSTAR\eltun:(DENY)(WD,AD)` and `A R`.
- Production target has hardlink count `2`; twin: `C:\Users\eltun\Documents\.tmp.driveupload\320360`.
- The two production-targeting `malt-radar-auth-b2` uvicorn processes were stopped at `2026-08-14T07:16:11+0300`.
- No baseline update, production write, ACL change, or push was performed by the containment audit.

## Evidence files

- `identity_propagation_apply.py` — frozen byte copy of the untracked candidate implementation.
- `identity_propagation_dryrun.py` — frozen byte copy of the untracked candidate dry-run implementation.
- `evidence_hashes.txt` — SHA-256 of both frozen copies and source copies at capture time.

The frozen copies are evidence only. Do not execute them.

## Stability observation contract

Containment observation begins after the two uvicorn processes are stopped.

- Window: **24 hours** minimum.
- Sampling: **once per hour**.
- Required samples: **25 samples** (`t=0` plus 24 hourly samples).
- Pass criterion: all 25 samples have the same byte SHA, logical fingerprint, row counts, journal state, and candidate-set hashes.
- Any SHA or logical fingerprint change is a FAIL and restarts attribution; no baseline update is allowed.
- Any candidate-set or logical-content change is a FAIL even if row counts remain constant.
- The watcher is read-only against production (`mode=ro`); its log is non-production evidence.

## Governance decision

`2e46abd5c8cea920c5e966c45f9ca8555c34b8d2` is recorded as an unauthorized/provisional closure-baseline commit made despite the active NO-GO decision. Its author metadata is generic and does not identify the originating session. This record is forward-only; no history rewrite is authorized.

`cbffd16b…` is not a trusted baseline until the ancestry gap and containment observation pass are independently verified.

## Stop condition

Do not run an apply, promotion, migration, baseline update, or Phase 2 work during this incident.
Do not push while the incident remains open.
