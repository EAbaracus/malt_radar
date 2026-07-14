# Certification Paths — MR-KEP P63

> Spec only, deterministic, evidence-first, read-only. Companion to
> `authority/confidence.yaml`, `templates/certification.yaml`, and the
> Certification Agent role in `AGENTS.md`. P63 defines the PATH by which a
> resolved value reaches certification; it performs no certification itself.

A **certification path** is the deterministic route a resolved (entity, field)
value takes to become *certified knowledge*. The path depends on the winning
source's tier, the field's authority ceiling, and how many independent sources
corroborate.

## The `certification_source` column

The resolution matrix assigns each (entity, field) a `certification_source` —
the tier whose confirmation is REQUIRED to certify that field:

| Field type | certification_source | Meaning |
|------------|----------------------|---------|
| identity | T1_authoritative | Only a T1 source can certify identity. |
| official_bottling | T1_authoritative | Only a T1 source can certify official facts. |
| sensory_evaluation | T2_expert | Expert tier certifies sensory. |
| scored_assessment | T2_expert | Expert tier certifies score. |
| supporting | T3_community | Community may certify only supporting facts. |

## Certification paths (deterministic)

### Path A — Direct certification (happy path)
```
winning source tier == certification_source
AND confidence >= certify_min (0.70)
  -> CERTIFIED. Evidence record attached (evidence.schema.json).
```

### Path B — Corroborated certification (raises confidence)
```
winning source tier == certification_source
AND >=1 independent verification_source agrees
  -> agreement bonus applied -> CERTIFIED at higher confidence.
```

### Path C — Proposed, pending higher tier (below-ceiling)
```
field ceiling == T1  BUT  only a T2/T3 source yielded a value
  -> NOT certified as the field.
  -> status = PROPOSED_NEEDS_CERT; retained as evidence;
     low-authority penalty applied; awaits a T1 confirmation.
```

### Path D — Conflict routed to certification
```
sources conflict AND merge policy cannot resolve
  -> status = UNRESOLVED_CONFLICT; all candidates retained;
     conflicting-unresolved penalty applied; human/audit review required.
```

### Path E — Below-threshold
```
winning source tier == certification_source
BUT confidence < certify_min (0.70)
  -> NOT certified; status = LOW_CONFIDENCE; flagged for more coverage.
```

### Path F — Uncovered
```
no source yields a value
  -> status = UNCOVERED; nothing certified; nothing fabricated.
```

## Confidence gates (from `authority/confidence.yaml`)

| Gate | Threshold | Effect |
|------|-----------|--------|
| certify_min | 0.70 | Below → not certified (Path E). |
| audit_warn_below | 0.60 | Certified but flagged for audit review. |
| merge_min | 0.50 | Below → cannot enter merge as a winner. |

## Sole-source rule

A field is never certified from a single **T3 (community)** source
(`templates/certification.yaml → sole_source_forbidden_tiers`). Community may
raise confidence via agreement but cannot be the sole certifier of any
non-supporting fact.

## Promotion is deferred

Certification produces staging evidence only. Writing certified knowledge into
`production.db` happens later, behind an explicit, separately-approved apply gate
with backup + rollback (mirroring Malt Radar P39/P42). P63 plans paths; it writes
nothing.

## Output (contract)

```
entity_key, field
winning_source_class, winning_tier
certification_path: A | B | C | D | E | F
certified: bool
confidence
status: CERTIFIED | PROPOSED_NEEDS_CERT | UNRESOLVED_CONFLICT |
        LOW_CONFIDENCE | UNCOVERED
evidence_ref
```

Deterministic: identical resolved inputs always yield the identical path.
