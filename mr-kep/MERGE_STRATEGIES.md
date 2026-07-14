# MERGE_STRATEGIES — MR-KEP Conflict Resolution

This document explains how MR-KEP resolves conflicting extractions. It is the
human-readable companion to `authority/merge_policies.yaml` and
`authority/field_rules.yaml`. The AOUS Merge Agent implements exactly what is
described here.

## Core principle

When two sources disagree on a field, the resolution is **deterministic** and
**authority-aware**, never a random pick or an undefined average.

## Resolution order

1. **Authority tier** — higher tier wins
   (`T1_authoritative` > `T2_expert` > `T3_community`).
2. **Source priority** — within the same tier, lower `priority` number wins
   (see `authority/source_priority.yaml`).
3. **Named merge policy** — applied per field (see below).
4. **Route to audit** — if none of the above yields a single value, the fact is
   routed to the Audit Agent with `UNRESOLVED_CONFLICT`.

## Named policies

### authority_wins
Highest tier (then priority) wins. Loser kept as evidence. Used for identity and
official-bottling fields: `distillery_name`, `region`, `country`, `abv`,
`age_statement`, `cask_type`.

### latest_expert_wins
Among T2 experts, the most recent `source_date` wins. Used for sensory fields:
`nose`, `palate`, `finish`, `flavor_axes`, `score`. Requires `source_date`;
missing date ⇒ policy fails ⇒ audit.

### consensus_additive
Group by normalized value; if ≥2 independent sources agree, mark agreed and add
the agreement bonus (from `confidence.yaml`). Used for `flavor_axes`,
`community_rating`.

### keep_all_supporting
Emit primary value per `authority_wins`; store every other candidate under
`provenance.evidence[]`. Never drops a loser. Used for `community_rating`.

### reject_on_conflict
For identity fields (`distillery_name`, `region`, `country`): if T1 candidates
conflict and cannot be resolved deterministically, REJECT the fact entirely and
route to audit. We never certify a contradictory identity.

## IoU matching before merge

Two extracted units are merged only if their IoU on
`[normalized_name, vintage, abv]` ≥ `iou_threshold` (default 0.85). Below that,
they are distinct whiskies and are never merged.

## Independence rule

The agreement bonus counts only **independent** sources — the same publisher
under different URLs does NOT count as two agreeing sources.

## No fabrication in merge

If no source states a field, the merged value is `null`. We do not synthesize a
value to resolve a conflict.
