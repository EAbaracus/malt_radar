# Merge Strategy — MR-KEP (detailed)

Detailed reference for the Merge Agent. Companion to `MERGE_STRATEGIES.md` and
`authority/merge_policies.yaml`.

## Inputs to a merge decision

For a given whisky (units matched by IoU ≥ 0.85), the Merge Agent gathers, per
field, a set of candidate `(value, source_key, tier, priority, source_date,
quote)` tuples.

## Decision algorithm (per field)

```
1. Filter candidates to those passing validation (authority ceiling OK).
2. If exactly one candidate  -> select it.
3. If multiple:
   a. Sort by (tier_rank asc, priority asc).
   b. Apply the field's named merge policy (see policies below).
   c. If policy yields one value -> select; mark winner won=true.
   d. If policy cannot resolve -> route to Audit (UNRESOLVED_CONFLICT).
4. Attach ALL candidates (winner + losers) to provenance.evidence[].
```

## Policy details

### authority_wins
Select the first after sorting by `(tier_rank, priority)`. Used for identity and
official-bottling fields. Losers retained.

### latest_expert_wins
Filter to T2; sort by `source_date` desc; select first. If no `source_date`,
policy fails → audit. Used for sensory + score.

### consensus_additive
Group by normalized value; if ≥2 **independent** sources share a value, mark
agreed and add the agreement bonus. Used for flavor_axes, community_rating.

### keep_all_supporting
Emit primary per `authority_wins`; keep all others as evidence. Used for
community_rating.

### reject_on_conflict
For identity fields: if T1 candidates conflict and no deterministic resolution
exists, REJECT the fact and route to audit. Never certify a contradictory
identity.

## IoU matching

```
iou = |intersection(match_on)| / |union(match_on)|
match_on = [normalized_name, vintage, abv]
threshold = 0.85   # configurable via merge_strategy.yaml
```

Below threshold ⇒ distinct whiskies, no merge.

## Independence

Agreement bonus counts only independent sources. Same publisher, different URL =
one source.

## Output

A merged record per whisky with, for each field, a winning value + full
provenance (winner flagged, losers retained) + `decided_by_policy`. Unresolved
conflicts are emitted as audit-routed items, never silently dropped or averaged.
