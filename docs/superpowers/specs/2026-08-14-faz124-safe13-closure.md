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

### Provenance gap — unresolved

The `70fa9cf0 -> 9e86cdac` transition is **not proven WAL-only and is not fully explained**. The preserved `70fa` backup has `W003023.distillery_id = D1687`; the live `cbffd` state has `D0255`. A row-level comparison against the `70fa` backup finds the five expected Faz-3 variant changes **plus W003023**. No byte-identical `9e86` backup exists in the retained backup set, so the exact point at which W003023 changed relative to the `9e86` boundary cannot be reconstructed from current artifacts. The Safe-13 driver did record `9e86` as its pre-SHA and then applied W003023, but that does not explain why the older `70fa` state differs by W003023 before the `9e86` boundary. This is a provenance gap, not evidence that the Safe-13 SQL was wrong.

The 12 distillery rows are the Safe-13 master-country updates. The effective Safe-13 pre-state is operationally `9e86cdac…`, but its ancestry from the last fully retained `70fa` state remains **OPEN / PROVISIONAL** until an independent `9e86` copy, WAL archive, or gate-native Faz-3 closure containing the exact post-state is recovered.

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

**Verdict:** TECHNICALLY VERIFIED / PROVISIONAL. Production mutation QA passed, but baseline ancestry remains OPEN due to the unresolved `70fa -> 9e86` provenance gap. Faz 2 distillery-binding (remaining 660-scale design) is not started.

## Change control

This closure is the persistent record required before updating the production baseline. No commit/push is included in this file's creation.
 yapildi.
  