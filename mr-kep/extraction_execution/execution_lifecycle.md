# Execution Lifecycle — MR-KEP P68

> Architecture/specification only. No implementation, OCR, parser, AI, or
> production interaction. References P62–P67; does not modify them.

## Stages (linear, deterministic)

```
Qualified ─▶ Waiting ─▶ Extracting ─▶ Evidence Recording ─▶ Validation
   │                                                           │
   └──────────────────────── ( Completed ) ◀── Certification Ready ◀┘
                                   │
                          (Rejected / Failed / Retry Pending / Rolled Back)
```

1. **Qualified** — document passed P67 qualification; a `qualification_record`
   (P67) exists. Entry into the execution pipeline.
2. **Waiting** — queued behind the deterministic priority order (P67 gate band:
   High Priority first, then Extract Normally, then Extract Later). No work yet.
3. **Extracting** — the extraction step runs per the P65 `extraction_request`
   against the `source_profile`. Produces a **draft** `extraction_result`
   (not yet evidenced).
4. **Evidence Recording** — each non-null field in the draft is written as an
   immutable P64 ledger entry (`evidence_id` derived from `evidence_hash`).
   This is the *only* stage that emits evidence.
5. **Validation** — the P65 `validation_contract` runs; produces a
   `validation_report` with gate PASS/PARTIAL/FAIL.
6. **Certification Ready** — validation PASS/PARTIAL and all certification entry
   requirements hold; the entity is handed to the Certification Agent (Sprint 2).
7. **Completed** — terminal success (certification bundle produced downstream).

## Checkpoints

A checkpoint is written at the **end of each stage** as a P65 bundle with a
SHA-256 `checksum` recorded in the run manifest (`manifests/*.yaml`, Sprint 1).

| Stage end | Checkpoint object | Type |
|-----------|------------------|------|
| Qualified | `input_manifest` snapshot | manifest |
| Waiting→Extracting | `extraction_request` | P65 contract |
| Extracting | `extraction_result` (draft) | P65 canonical output |
| Evidence Recording | `evidence_bundle` | P65 bundle (P64 entries) |
| Validation | `validation_report` | P65 contract |
| Certification Ready | `certification_bundle` (pre-handoff) | P65 bundle |

Resume rule (HERMES): on restart, load the last stage whose checkpoint checksum
verifies; re-run only that stage and forward. Stages before it are not repeated.

## Evidence-generation timing

- **Extracting** produces values but **no evidence entries** (draft only).
- **Evidence Recording** is where `evidence_id`, `retrieval_hash`,
  `evidence_hash`, and the four P64 hashes are computed and appended.
- This ordering guarantees the evidence-first rule: a value cannot reach
  Validation without a corresponding immutable ledger entry.

## Completion criteria

- `validation_report.gate ∈ {PASS, PARTIAL}`
- every non-null `metadata` field has ≥1 `evidence_id` in `evidence_bundle`
- `certification_per_field` populated
- `checksum` of `certification_bundle` recorded in manifest

Then state → Completed.

## Failure handling (summary; full detail in `retry_and_recovery.md`)

- Validation FAIL → Failed (or Retry Pending if recoverable).
- Ledger write error → Rolled Back to pre-Extracting checkpoint (ledger kept).
- License/OCR/authority failure → terminal Rejected, routed back to P67.

## No production interaction

No stage writes `production.db`. Certification handoff produces a bundle only;
the apply gate (Sprint 2) performs any production promotion under an explicit,
separately-approved transaction.
