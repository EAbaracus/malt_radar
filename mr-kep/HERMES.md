# HERMES — MR-KEP Operating Rules

These are the working rules Hermes (and any AOUS agent) MUST follow when
operating MR-KEP. They are binding for Sprint 1 and onward.

## 1. Deterministic execution
- Every run is reproducible: same inputs + same config ⇒ byte-identical outputs.
- A fixed `seed` is set in the manifest; ordering (tie-breaks, sort) uses it.
- No LLM-temperature-dependent logic in scoring or routing.
- Confidence math uses fixed decimals (`round_half_even`, 4 dp) from
  `authority/confidence.yaml` — no float drift between runs.

## 2. Evidence-first
- No fact is asserted without a quoted source excerpt (`quote`) and a
  `source_url`.
- `evidence_type` must be one of the keys in `confidence.yaml`
  (`primary_source_quote`, `bottle_print`, `expert_quote`, `aggregated_link`,
  `inferred`).
- `inferred` carries the lowest base confidence (0.20) and can never be the
  sole certifier of a fact.

## 3. Provenance tracking
- Every extracted/merged/certified value records its origin
  (`source_key`, `source_url`, `quote`, `source_date`).
- On conflict, the winning value is marked `won: true`; losing candidates are
  RETAINED in `provenance.sources` (never dropped) so the audit trail is intact.

## 4. Retry history
- Each source declares a deterministic retry policy (`max_attempts`,
  `backoff_seconds`, `record_history`).
- Every retry attempt is logged with timestamp + outcome. No silent retries.
- Retries never change the logical result set — they only recover transient
  failures. A different result after a retry is treated as a defect to audit.

## 5. IoU threshold
- Before merging, two extracted units must be judged the SAME whisky using an
  Intersection-over-Union (IoU) match on `match_on`
  (`normalized_name`, `vintage`, `abv`).
- Default `iou_threshold = 0.85` (configurable per merge strategy).
- Below threshold ⇒ treated as different whiskies; no merge.

## 6. Merge strategies
- Conflicts resolved by named policies in `authority/merge_policies.yaml`
  (`authority_wins`, `latest_expert_wins`, `consensus_additive`,
  `keep_all_supporting`, `reject_on_conflict`).
- Resolution order: highest authority tier → source priority → named policy.
- Unresolvable conflicts are routed to the Audit Agent with
  `reason = UNRESOLVED_CONFLICT`; they are NEVER silently dropped or averaged.

## 7. Checkpoint system
- Each stage writes a checksummed artifact; the manifest records
  `input_ref` / `output_ref` / `checksum` per stage.
- A run can be resumed from the last passed stage using these checkpoints.
- Checkpoint files are content-addressed by SHA-256 so re-runs are verifiable.

## 8. No fabrication
- If a source does not state a field, the value is `null`.
- We never invent values, scores, or quotes to satisfy a schema.
- Empty is preferred over false precision.

## 9. Read-only verification
- This foundation (Sprint 1) reads standards only; it writes no production data.
- Certified records are promotion-ready but are NOT written to `production.db`.
- Any future production apply is gated behind an explicit, separately-approved
  apply gate with backup + rollback — mirroring the Malt Radar P39/P42 pattern.
- Verification of deliverables is read-only; a failed verifier is reported, not
  debugged endlessly.
