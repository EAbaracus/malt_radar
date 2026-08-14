# Faz 1/2/4 Safe-13 Closure

**Phase:** `faz124_safe13`  
**Status:** CLOSED  
**Human GO:** `WRITE GO: identity repair faz124 safe13`

## SHA chain and drift resolution

- Prior verified post-identity-repair state: `70fa9cf001c981af991c7382485378ac9caa607b98a7168f54fc9bcfb0f208e3`
- Evidence: `output/import/backups/production_prepromote_20260814_003211.db`
- Backup SHA: exactly `70fa9cf001c981af991c7382485378ac9caa607b98a7168f54fc9bcfb0f208e3`
- Safe-13 pre-apply state: `9e86cdacb0a3bbc38b4bcc5d147f834e56d81a862fe406de3f925fb33767fecb`
- Safe-13 post-apply state: `cbffd16b29433c983bb113b2e9a9f186dd94c1ff9dc6f5f1b13d97f084386177`

### Provenance resolution

The `70fa9cf0 -> 9e86cdac` transition is **fully explained as the Faz-3 canonical merge**, not WAL-only drift and not an external mutation. The retained snapshots were compared at the correct boundary:

```text
production_prepromote_20260814_004512.db (70fa)
→ production_pre_faz124_safe13.db (9e86)
```

The row-level diff contains exactly five changed `whiskies` rows, each changing only `superseded_by`:

```text
W002097 → W001322
W002278 → W000862
W002411 → W001109
W002931 → W000543
W003068 → W000599
```

`W003023` is unchanged in both snapshots (`D1687`, `Cork`, country NULL, not superseded). The earlier apparent extra difference came from the incorrect comparison of the older `70fa` snapshot directly against the final `cbffd` state, which conflated the later Safe-13 changes with the Faz-3 transition. The 12 distillery rows changed only in `9e86 → cbffd`, exactly matching Safe-13's 12 master-country updates. Baseline ancestry is now **RESOLVED**.

## Applied scope

- One rebind: `W003023`, `D1687` → `D0255` (`Clonakilty Distillery`).
- Twelve `distilleries.country` updates: D1078, D1308, D1733, D1335, D1204, D1004, D1035, D1684, D1742, D1021, D1730, D1740.
- Woodford Reserve ×11, House Of Hazelwood ×8, Booker's, The Hearach, Malloy Hall, and W002906 remain HUMAN_REVIEW.

## W002906 ligature collision

`W002906` had T1 candidate `Glenﬁddich` (D1091), while its current binding is D0010 `Glenfiddich`. NFKD normalization removes the `ﬁ` ligature, making both master names the same normalized key. Multiple master rows therefore collide on one identity key. The hardened resolver forbids automatic binding on collided keys; W002906 remains HUMAN_REVIEW. No update was applied.

## T1 governance finding

The prior candidate builder omitted two required filters: master head-cluster size ≥2 → HUMAN_REVIEW, and unknown target country (`country=None`) → no automatic bind. This generated the 11 false-positive Woodford/producer/expression candidates; all were caught before apply and withheld. The gap is a builder defect, not evidence for those bindings.

Booker's master rows also carry `country='Scotland'`; this is recorded as a master-data-quality backlog item, not silently corrected in Safe-13.

## Verification

- Dry-run: 13 updates, FK=0, integrity=ok.
- Live post-QA: whiskies=4,750; flavor_evidence=6,367; flavor_profiles=4,409; active/superseded=4,593/157.
- `W003023.distillery_id = D0255`; 12/12 master-country updates verified.
- FK violations=0; `PRAGMA integrity_check=ok`; DENY ACE `(WD,AD)` present.
- Backup SHA matched Safe-13 pre-SHA.
- No evidence/profile rows changed; no merge/supersede was performed by Safe-13.

## Artifacts

- `output/import/backups/production_pre_faz124_safe13.db`
- `%LOCALAPPDATA%\Temp\mr_faz124_plan\faz124_apply_report.json`
- `%LOCALAPPDATA%\Temp\mr_faz124_plan\faz124_plan.json`
- `%LOCALAPPDATA%\Temp\mr_faz124_plan\faz1_junk_rebind_plan.csv`
- `%LOCALAPPDATA%\Temp\mr_faz124_plan\faz2_rebind_candidate_plan.csv`
- `%LOCALAPPDATA%\Temp\mr_faz124_plan\faz4_master_country_plan.csv`

**Verdict:** GO / CLOSED. Production mutation QA passed and the `70fa -> 9e86` ancestry is resolved by the exact five-row Faz-3 snapshot diff. Faz 2 distillery-binding (remaining 660-scale design) is not started.

## Change control

This closure is the persistent record required before updating the production baseline. No commit/push is included in this file's creation.
 yapildi.
  