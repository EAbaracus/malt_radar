# P203 — Executive Summary (Distillery Crosswalk Intelligence)

> READ-ONLY design audit. No SQL, no writes, no commits. Deliverables only under `mr-kep/p203_distillery_crosswalk/`.

## Root cause of matching failure
- External CSVs carry **free-text distillery names**; production uses a proper **`distilleries` dimension**
  (`distillery_id` + `name`, plus region/owner/wikidata). The KEY SCHEME differs → P202B's 17 NO_MATCH.
- knowledge.db has **0 distillery names** — production `distilleries` is the canonical source-of-truth.

## What was discovered
- 3148 distinct distillery representations across 4 sources.
- 60 multi-representation groups (e.g. Macallan = 'Macallan' + 'The Macallan').
- Mismatch taxonomy confirmed: distillery-suffix (438), unicode (219), punctuation (159), owner-suffix (63), the-prefix (51), apostrophe (42), ltd-suffix (24), marketing-suffix (27), region-suffix (11).

## Recovery estimate
- **15/17** P202B NO_MATCH rows resolve via a simple canonical-key crosswalk (~88%).
- Residual 2 are coverage gaps (bourbon/blend brands), not logic failures.

## Deliverable: crosswalk schema (design)
- Table `distillery_crosswalk` with: entity_id (→distilleries.distillery_id), canonical_name, external_name, source, confidence, match_method.
- Append-only, reviewed; confidence<0.7 → MANUAL_REVIEW (mirrors P200/P202 gating).

## Final verdict
**GO (design-ready).** The canonical distillery identity model is fully specified and evidence-backed.
Implementation is the natural next authorized step (a P203B WRITE task) — build the table, run normalization,
queue <0.7 rows for manual review. This single asset unlocks future matching across all external sources.
