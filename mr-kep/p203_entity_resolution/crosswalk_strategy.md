# P203 — Crosswalk Strategy

## What exists
- `mr-kep/p129_crosswalk/` — `uuid_whisky_crosswalk.csv` (475 rows),
  `crosswalk_nomatch.csv` (315), `crosswalk_collisions.csv` (0).
- Input: production.whiskies = 3,959 W-ids + 790 UUID-ids; SMWS-code overlap
  `uuid ∩ W = 0` (no direct code bridge).
- Confidence: EXACT 0, STRONG 4, MEDIUM 6, WEAK 465, NO_MATCH 315.
- The 4 STRONG are expression-level mismatches (single-cask vs core-range) — false-positive risk (`p132`).

## Decision (D5, `p137a_crosswalk_necessity_assessment.md`)
- Crosswalk is **NOT required for SMWS promotion (P137B)** — `promotion_queue.entity_key`
  already holds the production whisky_id resolved at ingest.
- Crosswalk is **DEFERRED** to a future book-promotion task.
- The crosswalk CSV **stays in staging and is NOT loaded into knowledge.db**.

## P203 canonical crosswalk policy
1. **Do not auto-load P129.** Its 475 weak matches (0.50–0.60) would inject low-confidence
   UUID→W merges into production — exactly the identity risk AGENTS.md warns against.
2. **Activation gate:** a crosswalk row may enter the canonical model ONLY if:
   - `EXACT` (distillery + age + name exact), OR
   - `STRONG` AND expression-level check passes (same bottling class), OR
   - human-reviewed and accepted via `review_queue`.
3. **Storage:** when activated, persist as `entity_external_links`
   (`link_type='official'`, mapping UUID entity → W entity) plus a `merge_history` row
   (idempotent `dedupe_key`). Do NOT alter `whiskies` PKs.
4. **Collisions:** P129 had 0 collisions; any future collision (≥2 candidates ≥0.7) →
   `review_queue` issue_type `conflict`, never silent pick.
5. **Book pipeline bridge:** book-sourced `evidence.entity_key` UUIDs that lack a
   production whisky_id are the ONLY consumers of the crosswalk; everything else joins
   via `promotion_queue.entity_key`.
6. **Future source IDs (P300/P400):** new external IDs (Whiskybase, MasterOfMalt) enter
   via `external_entities` + `entity_external_links`, treated as crosswalk entries under
   the same activation gate.

## Reuse, don't replace
- The P129 CSV + validation scripts are the canonical crosswalk artifact. P203 references
  them; it does not rebuild them.
- `merge_history.dedupe_key` (UNIQUE) is the idempotency guarantee for any activated link.
