# Fallback Chains — MR-KEP P63

> Spec only, deterministic, evidence-first, read-only. Companion to
> `resolution/source_resolution_matrix.csv`.

A **fallback chain** is the ordered list of source classes the resolver attempts
only when every `preferred_source_order` class fails to yield a field. Chains are
deterministic (left-to-right) and authority-aware (a fallback never overrides a
higher-tier value; it only fills a gap, at reduced confidence).

## Notation

`A > B > C` means: try A; if A yields nothing, try B; then C. The first class
that yields a value wins its slot. A value obtained from a fallback carries the
fallback source's tier and evidence type, and therefore its confidence ceiling.

## Field-type fallback chains (default, all entities)

| Field type | Preferred order | Fallback chain | Verification |
|------------|-----------------|----------------|--------------|
| identity | official > regulatory > official_wayback | book > expert_review | regulatory |
| official_bottling | official > official_wayback > regulatory | structured_metadata > book > expert_review | structured_metadata |
| sensory_evaluation | expert_review > book | community | book |
| scored_assessment | expert_review | community | expert_review |
| supporting | community | *(none)* | community |

## Entity-specific overrides

### bottling · official_bottling
Independent bottlings often lack an OB technical sheet, so the bottler's own
product data IS the `official` source and structured metadata is promoted into
the preferred order:

- Preferred: `official > official_wayback > structured_metadata`
- Fallback: `book > expert_review`
- Verification: `expert_review`

### distillery · identity (incl. closed distilleries)
For closed/silent distilleries live official is usually gone; `book` is promoted
into the preferred order and `official_wayback` carries identity:

- Preferred: `official > regulatory > official_wayback > book`
- Fallback: `expert_review`
- Verification: `regulatory`

## Authority ceiling enforcement in fallbacks

A fallback may PROPOSE a value for a field whose ceiling is above the fallback's
tier (e.g. `expert_review` proposing `abv`, a T1 field). Rules:

1. The proposed value is retained as **evidence**, not certified as the field.
2. Confidence is penalized (`penalties.low_authority_tier` in
   `authority/confidence.yaml`).
3. The item is flagged for the Certification path — a T1 field is only certified
   when a T1 source eventually confirms it.

## Exhausted chain → UNCOVERED

If both `preferred_source_order` and `fallback_chain` are exhausted with no
value, the resolver emits `status = UNCOVERED` for that (entity, field). It never
fabricates. UNCOVERED items drive the coverage plan (`coverage_resolution.md`),
not a NO_GO by themselves (unless an identity field is UNCOVERED — see
GO/NO-GO).

## Determinism

Chains are fixed lists in the model/matrix; given the same coverage signals, the
resolver produces the same plan every run. No randomness, no live fetch.
