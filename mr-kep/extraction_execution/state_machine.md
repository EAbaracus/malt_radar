# State Machine — MR-KEP P68

> Architecture/specification only. No implementation, OCR, parser, AI, or
> production interaction. References P62–P67; does not modify them.

## The 12 execution states

| # | State | Allowed transitions | Entry criteria | Exit criteria | Rollback point | Evidence emitted | Failure modes | Retry policy |
|---|-------|---------------------|----------------|--------------|----------------|-----------------|--------------|--------------|
| 1 | **Queued** | → Qualified | unit received from orchestrator | classification + qualification done (P67) | pre-pipeline | none | queue overflow | none (retry at ingest) |
| 2 | **Qualified** | → Waiting, → Rejected | P67 gate ∈ {Extract Later, Extract Normally, High Priority} | priority slot assigned | pre-pipeline | none (qualification_record from P67) | license failure, authority failure | none (terminal Rejected) |
| 3 | **Waiting** | → Extracting, → Rejected | priority slot reached | extraction_request built (P65) | pre-Extracting | none | source gone (404) | recoverable → Retry Pending |
| 4 | **Extracting** | → Evidence Recording, → Failed, → Retry Pending | extraction_request valid | draft extraction_result produced | pre-Extracting | none (draft only) | transient fetch error, parse timeout | recoverable → Retry Pending (≤3) |
| 5 | **Evidence Recording** | → Validation, → Rolled Back | draft result present | all non-null fields → immutable P64 entries | pre-Extracting (ledger preserved) | P64 ledger entries (EV- ids) | ledger write error | Rolled Back (never silent) |
| 6 | **Validation** | → Certification Ready, → Failed, → Retry Pending | evidence_bundle present | validation_report gate ∈ {PASS, PARTIAL} | pre-Extracting | none new (report only) | schema violation, null-policy breach | recoverable → Retry Pending |
| 7 | **Certification Ready** | → Completed, → Rejected | certification entry requirements met | certification_bundle pre-handoff produced | pre-Certification | certification_bundle (refs EV- ids) | manual-review needed | manual-review (no auto) |
| 8 | **Completed** | (terminal) | certification handed off | — | — | final bundle | — | — |
| 9 | **Rejected** | (terminal) | license/authority failure, or validation FAIL non-recoverable | — | — | none | — | manual-review |
| 10 | **Failed** | → Retry Pending, → Rolled Back | retry budget exhausted or non-recoverable error | — | pre-Extracting | partial ledger (kept) | — | terminal if budget out |
| 11 | **Retry Pending** | → Waiting/Extracting, → Failed | recoverable failure, attempts < MAX_RETRIES | wait elapses (deterministic backoff) | pre-Extracting | none new | — | auto after backoff |
| 12 | **Rolled Back** | → Waiting, → Failed | rollback triggered (ledger error / manual) | checkpoint restored | pre-Extracting | ledger preserved (quarantined rows) | — | re-enter at Waiting |

## Transition invariants (deterministic)

- A transition fires only when its entry criteria AND exit criteria both hold,
  evaluated by a deterministic check (gate / checksum / validation).
- `Evidence Recording → Validation` requires `len(evidence_bundle) >=
  count(non-null fields)` (evidence-first).
- `Validation → Certification Ready` requires `gate ∈ {PASS, PARTIAL}`.
- `Rolled Back` never deletes P64 entries (append-only / immutable, AR-1/AR-3).
- `Rejected` and `Failed` are terminal unless a manual-review gate re-opens them.

## State diagram (text)

```
Queued → Qualified → Waiting → Extracting → Evidence Recording → Validation
                                          │                      │
                                          │                      ├─(PASS/PARTIAL)→ Certification Ready → Completed
                                          │                      └─(FAIL,recov)→ Retry Pending → Waiting
                                          └─(ledger error)→ Rolled Back → Waiting
Extracting ─(transient)→ Retry Pending
Validation ─(FAIL,non-recov)→ Failed → (budget?) Rolled Back / Rejected
Qualified ─(license/authority)→ Rejected
```
