# P137A — Crosswalk Necessity Assessment

- doc_version: P137A-1
- date_utc: 2026-07-17
- question: is the P129 crosswalk (475 weak UUID<->W matches) required for P137B?

## P129 crosswalk facts (re-stated)
- `uuid_whisky_crosswalk.csv` = 475 rows, ALL weak (0 exact, 0 strong; 423 distillery-only @0.60, 52 partial).
- `crosswalk_nomatch.csv` = 315 rows (no match).
- `crosswalk_collisions.csv` = 0 rows.
- Source: production.whiskies (3,959 W-ids + 790 UUID-ids). SMWS-code overlap uuid∩W = 0.

## Does P137B (SMWS promotion) need it?
**NO.** Proof by schema:
- `promotion_queue.entity_key` already holds the **production `whisky_id`** (resolved at
  P136 ingest time from `production.flavor_evidence.whisky_id`).
- `normalized_metadata.entity_key` = same production whisky_id.
- P137B reads `promotion_queue` → applies to `production.whiskies(whisky_id)` via the
  P121 gate. No UUID<->W translation occurs.

The crosswalk would ONLY be needed if P137B promoted **book-sourced UUID entities** that
must be mapped to W-ids. That is a separate future workstream (book promotion), not the
SMWS path.

## Risk of using the crosswalk now
- 475/475 are WEAK (0.50–0.60). Auto-applying them would inject low-confidence
  UUID→W merges into production — exactly the identity risk AGENTS.md warns against.
- P129 itself returned WARN_GO (not GO) because exact/strong = 0.

## Decision (logged as D5)
- **Crosswalk NOT required for P137B (SMWS).**
- **DEFER** crosswalk integration to a dedicated future task (e.g. book-promotion prep),
  gated on obtaining exact/strong matches (or human review of the 475 weak).
- Until then, the crosswalk stays in `mr-kep/p129_crosswalk/` (staging) and is NOT
  loaded into knowledge.db.
