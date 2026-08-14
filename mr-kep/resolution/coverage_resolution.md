# Coverage Resolution — MR-KEP P63

> Spec only, deterministic, evidence-first, read-only. No fetching in P63.
> Companion to `resolution/source_resolution_model.yaml → coverage_signals`.

The **Coverage Resolver** computes, for a given entity, a set of deterministic
boolean *coverage signals* that describe WHICH source classes are expected to be
available. These signals drive which branch of the resolution plan is taken. In
P63 the signals are a **planning contract** — the actual population of the
signals (by probing sources) happens in a later phase; here we define the
questions, their inputs, and how each answer steers resolution.

## Coverage signals

| Signal | Source class | Question | Steers |
|--------|-------------|----------|--------|
| official_available | official | Is a live official source present? | If true → identity/official_bottling resolve directly. |
| wayback_required | official_wayback | Is official gone/changed so an archived snapshot is needed? | If true → use official_wayback (T1, `archived_snapshot`). |
| book_support | book | Is there published reference-book support? | Enables book fallback / closed-distillery identity. |
| expert_review_available | expert_review | Is an expert review present? | If true → sensory/score resolve at T2. |
| structured_metadata | structured_metadata | Is structured metadata present? | Corroborates official_bottling. |

## Deterministic decision procedure

For each (entity, field) the resolver walks the plan in this fixed order:

```
1. If official_available:
      use official (T1). If structured_metadata -> corroborate. DONE.
2. Elif wayback_required AND an archived official snapshot exists:
      use official_wayback (T1, provenance=archived_snapshot). DONE.
3. Elif field_type is T1 (identity/official_bottling):
      no T1 coverage -> walk fallback_chain to PROPOSE (not certify) a value;
      mark needs_certification=true (T1 field lacking T1 source). 
4. Elif field_type is sensory/score (T2 ceiling):
      if expert_review_available -> use expert_review (T2);
      elif book_support -> use book (T2);
      else -> community fallback (T3) at low confidence.
5. If NO class yields a value -> status = UNCOVERED (never fabricate).
```

The procedure is total and deterministic: identical coverage signals always
produce the identical plan.

## Coverage → confidence coupling

Coverage breadth feeds confidence via `authority/confidence.yaml`:

- **1 source covering a field** → base confidence only.
- **≥2 independent sources** covering + agreeing → agreement bonus (capped).
- **Only a below-ceiling source covers a T1 field** → low-authority penalty +
  route to Certification.
- **No coverage** → UNCOVERED (no confidence; not a value).

## Coverage plan output (contract)

For each entity the resolver produces a coverage plan record (spec):

```
entity_key, entity_type
per_field:
  field, chosen_source_class, coverage_status
  coverage_status ∈ {COVERED_T1, COVERED_T2, COVERED_T3,
                     PROPOSED_NEEDS_CERT, UNCOVERED}
  independent_source_count
gaps: [ list of UNCOVERED or PROPOSED_NEEDS_CERT fields ]
```

This plan is the input to `certification_paths.md` and the GO/NO-GO evaluation.
No data is fetched or written to produce it — it is a deterministic projection
of the coverage signals over the resolution matrix.

## No fabrication / read-only

- Absent coverage is reported as UNCOVERED, never filled with an invented value.
- The Coverage Resolver reads standards + coverage signals only; it never writes
  production data and never fetches in P63.
