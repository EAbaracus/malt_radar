# Conflict Resolution — MR-KEP P63

> Spec only, deterministic, evidence-first, read-only. Companion to
> `authority/merge_policies.yaml` and `MERGE_STRATEGIES.md`. P63 defines how the
> resolution layer *routes* conflicts; the merge policies themselves live in the
> Sprint 1 authority layer.

A **conflict** occurs when two or more sources yield different values for the
same (entity, field). The resolution engine resolves conflicts deterministically
using the authority layer, and routes anything it cannot resolve to
Certification — never averaging, never a silent pick.

## Resolution order (deterministic)

```
1. Authority tier      — higher tier wins (T1 > T2 > T3).
2. Source priority     — within a tier, lower priority number wins
                         (authority/source_priority.yaml).
3. Named merge policy  — per field (authority/merge_policies.yaml):
                         authority_wins | latest_expert_wins |
                         consensus_additive | keep_all_supporting |
                         reject_on_conflict.
4. Route to Certification — if 1–3 yield no single value.
```

## Conflict classes and routing

| Conflict class | Example | Deterministic handling |
|----------------|---------|------------------------|
| Cross-tier | official ABV vs expert ABV | `authority_wins` → official (T1). Expert kept as evidence. |
| Same-tier, same field, dated | two expert scores | `latest_expert_wins` (needs source_date). |
| Same-tier, agreeing | two experts, same flavor axis | `consensus_additive` → agreement bonus. |
| Identity contradiction | two T1 sources disagree on region | `reject_on_conflict` → REJECT + route to Certification. |
| Below-ceiling proposal | expert proposes a T1 abv, no official | Not certified; low-authority penalty; route to Certification. |
| Supporting-only | community rating differs | `keep_all_supporting` → all kept as evidence. |

## Independence requirement

Agreement (consensus) counts only **independent** sources. Same publisher under
different URLs, or a mirror/aggregator echoing one origin, counts as ONE source.
The resolver deduplicates by origin before counting agreement.

## Unresolved conflict → Certification, not guess

When resolution order 1–3 cannot produce a single value:

- Emit a conflict record with `resolved=false`,
  `reason=UNRESOLVED_CONFLICT`.
- Retain ALL candidate values + provenance (losers never dropped).
- Route to the Certification path (`certification_paths.md`).
- Apply `penalties.conflicting_unresolved` from `authority/confidence.yaml`.

## What the resolver must NEVER do

- Never average conflicting numeric values.
- Never silently pick one of several equal candidates without a policy.
- Never fabricate a tie-break source.
- Never let a T3 (community) value override a T1/T2 fact.
- Never write production data while resolving.

## Output (contract)

```
conflict_id, entity_key, field
candidates: [ {value, source_class, tier, priority, source_date, quote} ]
decided_by_policy | null
winner_value | null
resolved: bool
reason
losers_kept: true            # always true; provenance preserved
routed_to: certification | none
```

Deterministic: identical candidate sets always resolve identically.
