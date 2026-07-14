# Provenance Model — MR-KEP P64

> Spec/docs only, deterministic, evidence-first, read-only, no fabrication.
> Companion to `evidence/evidence_schema.json` (`provenance_state`) and
> `evidence_lifecycle.md`.

Every evidence entry carries a `provenance_state` describing where it sits in
its life. The ledger is **append-only**: a state change never edits a row — it
appends a NEW entry that `supersedes` the previous one, preserving the full
chain.

## The seven provenance states

| State | Meaning | Entered when |
|-------|---------|--------------|
| `discovered` | A candidate source/location for a field was identified (per P63 resolution plan), no value extracted yet. | Resolver plans a source attempt. |
| `extracted` | A raw `field_value` + `selector` + `quote` was captured from the source. | Extraction Agent records the observation. |
| `normalized` | The raw value was canonicalized per `authority/field_rules.yaml`. | Validation Agent applies normalization. |
| `verified` | An independent `verification_source` (P63) corroborated the value. | A second, independent entry agrees. |
| `certified` | The value met its `certification_source` tier + `certify_min` (0.70) via a P63 path. | Certification Agent certifies. |
| `superseded` | A newer entry replaced this one (e.g. later expert review, corrected value). | A new entry `supersedes` this id. |
| `deprecated` | The value is retired (source retracted, proven wrong) but retained for audit. | Audit Agent deprecates; never deletes. |

## Allowed transitions (deterministic state machine)

```
discovered ──▶ extracted ──▶ normalized ──▶ verified ──▶ certified
                   │              │             │            │
                   ▼              ▼             ▼            ▼
               deprecated    deprecated    superseded   superseded
                                               │            │
                                               ▼            ▼
                                           deprecated   deprecated
```

Rules:
- Forward-only through the happy path (`discovered → … → certified`).
- Any state may go to `deprecated` (retire) — the entry is kept, not deleted.
- `verified`/`certified` may go to `superseded` when a newer entry wins.
- **No backward transitions** on the same entry (immutability); a "re-do" is a
  brand-new entry with its own `evidence_id`.
- A transition that changes any field is a NEW ledger row with `supersedes`
  pointing at the prior `evidence_id`.

## Provenance preservation

- Superseded and deprecated entries are **never removed**. Querying "current"
  values filters to the latest non-superseded, non-deprecated entry per
  `(entity_id, field_name)`; the history remains fully reconstructable.
- Each entry records its own `source_class`, `source_name`, `source_url`/
  `source_citation`, `selector`, and hashes, so provenance is self-contained per
  row — no external lookup needed to know where a value came from.

## Mapping to P63 & Sprint 1

| Provenance state | Produced by (agent, from P63/Sprint 1) |
|------------------|----------------------------------------|
| discovered | Resolver / Qualification Agent (P63 plan) |
| extracted | Extraction Agent |
| normalized | Validation Agent (`field_rules.yaml`) |
| verified | Validation/Merge using P63 `verification_source` |
| certified | Certification Agent (P63 paths A/B) |
| superseded | Merge Agent (`latest_expert_wins`, corrections) |
| deprecated | Audit Agent |

## Determinism & no fabrication

- The state machine is fixed; given the same events, the same states result.
- A state is only advanced by real evidence — `verified`/`certified` require
  actual corroborating entries, never an assumption.
- No state transition writes to production; P64 is a standard, not a runtime.
