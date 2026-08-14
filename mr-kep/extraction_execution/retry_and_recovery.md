# Retry & Recovery — MR-KEP P68

> Architecture/specification only. No implementation, OCR, parser, AI, or
> production interaction. References P62–P67; does not modify them.

## Deterministic retry constants

| Constant | Value | Source of truth |
|----------|-------|-----------------|
| `MAX_RETRIES` | 3 | fixed |
| `BASE_BACKOFF_MIN` | 5 | fixed (minutes) |
| Backoff schedule | 5, 10, 15 min | `BASE_BACKOFF_MIN × attempt` |
| `BLOCKED_CAP` | 5 | consecutive blocked → manual-review |

Attempt counting is deterministic: same failure signature ⇒ same attempt number
⇒ same backoff. No jitter, no randomness.

## Failure classes

| Class | Examples | Disposition | Auto-retry? |
|-------|----------|-------------|-------------|
| **recoverable** | transient fetch error, parse timeout, validation PARTIAL | Retry Pending (≤3) → Rolled Back | yes |
| **non-recoverable** | malformed source, schema violation after 3 tries | Failed → Rejected | no |
| **manual-review** | blocked > BLOCKED_CAP, ambiguous conflict, low-confidence cert | Rejected (manual-review) | no (human) |
| **blocked** | robots disallow, rate-limit, 429 | Retry Pending (capped at BLOCKED_CAP) → manual-review | yes (capped) |
| **license failures** | license_risk==1.0 (P67), TOS violation | Rejected (terminal) | no |
| **OCR failures** | ocr_need but no text layer (P67 G4) | Archive Only (P67) → Rejected for extract | no |
| **authority failures** | T3 ∧ identity<0.2 (P67 G3), no T1 for T1-ceiling field | Rejected → re-qualify | no |

## Retry policy (deterministic)

```
on failure F during {Extracting, Validation, Evidence Recording}:
  if F in {license, OCR, authority}:        → Rejected (terminal, no retry)
  if F == blocked and blocked_count >= 5:   → manual-review
  if F == blocked and blocked_count < 5:    → Retry Pending (backoff, capped)
  if F in {recoverable, non-recoverable}:
      attempts += 1
      if attempts <= 3:  → Retry Pending (backoff[attempts])
      else:              → Failed (or Rolled Back if ledger touched)
```

## Rollback rules

1. **Trigger:** any error in `Extracting`, `Evidence Recording`, or `Validation`
   that cannot complete the stage, OR an explicit manual rollback.
2. **Target:** restore the run to the **last valid checkpoint** (pre-Extracting
   for Extracting/Evidence/Validation; pre-Certification for Certification
   Ready). Checkpoint selection uses the recorded SHA-256 checksum (HERMES).
3. **Ledger safety (immutable):** the P64 Evidence Ledger is **never deleted or
   edited** on rollback. Any partial entries from the failed run are
   **quarantined** (state `deprecated` per P64) but retained for audit.
4. **Idempotency:** re-running from the checkpoint produces byte-identical
   bundles (deterministic seed/checksum), so rollback is safe to repeat.
5. **No production:** rollback performs no `production.db` write.

## Relationship to P67 / P64

- `license / OCR / authority` failures route back to P67 qualification (which
  holds the gate that produced them) — they are NOT retried in execution.
- `Evidence Recording` rollback relies on P64 AR-1 (immutable) + AR-2
  (append-only): the failed run's entries are kept, never overwritten.
