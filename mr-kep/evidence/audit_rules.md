# Audit Rules — MR-KEP P64 Evidence Ledger

> Spec/docs only, deterministic, evidence-first, read-only, no fabrication.
> These are the binding rules governing how the Evidence Ledger is written and
> audited. They align with the Malt Radar `AGENTS.md` (backup, evidence,
> escalation) and the Sprint 1 `HERMES.md` rules.

## AR-1 · Immutable evidence
- A written ledger entry is **never modified in place** and **never deleted**.
- `evidence_id` is derived from `evidence_hash`; any change to a stored entry
  breaks the id↔hash binding and is flagged as tampering by the Audit Agent.
- Corrections happen only by appending a NEW entry (see AR-2).

## AR-2 · Append-only ledger
- The ledger grows by append. A state change or value correction is a NEW entry
  that sets `supersedes` to the prior `evidence_id`.
- The prior entry transitions to `superseded` (or `deprecated`) but stays in the
  ledger for audit.
- "Current value" = the latest entry per `(entity_id, field_name)` that is
  neither `superseded` nor `deprecated`.

## AR-3 · Provenance preservation
- Every entry is self-describing: `source_class`, `source_name`,
  `source_url`/`source_citation`, `selector`, `retrieval_timestamp`, and the
  four hashes. Provenance can be reconstructed from the row alone.
- Losing candidates in a merge are retained (as `verified`/`superseded`), never
  dropped — the full evidence set behind any decision is queryable.

## AR-4 · No silent overwrite
- A newer value can never overwrite an older one without leaving a trace: the
  supersession is explicit (`supersedes` + state change) and both rows persist.
- A merge that changes the winning value must record `merge_strategy` and keep
  the losers. Any value change without a superseding entry is an audit failure.

## AR-5 · Full traceability
- Every emitted final value MUST trace back through:
  `Final Value → certified entry → merge (strategy) → evidence entries → source`.
- Any final value lacking a complete chain to at least one ledger entry is an
  audit failure (evidence-first: no fact without evidence).
- Certification of a T1-ceiling field MUST trace to a T1 source entry; a T1
  field certified from a T2/T3 entry is an audit failure.

## AR-6 · No fabrication
- `field_value = null` when a source did not state the field. An entry with a
  non-null value and no supporting `selector`/`quote`/`source` is an audit
  failure.
- `notes` may never carry a substitute value to bypass null.

## AR-7 · Hash integrity
- On audit, recompute `evidence_hash` from the entry's inputs and confirm
  `evidence_id == "EV-" + evidence_hash[:16]`.
- Recompute `retrieval_hash` from `source_url|retrieval_timestamp|content_hash`.
- Mismatch ⇒ the entry is quarantined (not deleted) and flagged.

## AR-8 · Read-only & deferred promotion
- Writing the ledger never writes `production.db`. Promotion of certified values
  into production happens only behind an explicit, separately-approved apply gate
  (mirrors Malt Radar P39/P42: backup + single transaction + rollback).
- Audit itself is read-only; it may flag/quarantine/deprecate (all append-only)
  but performs no destructive or production write.

## AR-9 · Determinism
- Given identical evidence events, the ledger content (ids, hashes, states) is
  identical across runs and machines. Non-determinism in id/hash generation is
  an audit failure.

## Audit checklist (per run)
- [ ] Every entry: `evidence_id == EV-<evidence_hash[:16]>` (AR-1, AR-7).
- [ ] No in-place edits (only appends); every value change has a `supersedes`
      link (AR-2, AR-4).
- [ ] Every current value traces to ≥1 ledger entry and its source (AR-5).
- [ ] Every T1 certified field traces to a T1 entry (AR-5).
- [ ] No non-null value without selector/quote/source (AR-6).
- [ ] `retrieval_hash` recomputes correctly (AR-7).
- [ ] `production.db` unchanged (AR-8).
