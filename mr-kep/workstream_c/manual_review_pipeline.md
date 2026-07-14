# Workstream C — Manual Review Pipeline

> Companion to `remediation_strategy.md`. The **human-decision layer** that all
> five remediation tracks (R1–R5) hand their non-auto-resolvable proposals to.
> **No production write. No schema change. Deterministic assignment. Evidence-first.**

## 1. Review buckets (from the policies)

| Bucket | Feeds from | Volume (upper bound) |
|--------|-----------|----------------------|
| `conflict` | CR-2 / CR-4 (unresolvable conflicts) | ⊆ 1,002 X rows |
| `lowconf` | CU-4 (E with no trusted corroboration) | ⊆ 441 E rows |
| `missing` | R3 no-candidate | ⊆ 375 missing |
| `tasting` | R4 generic/short un-enrichable | ⊆ 912 flagged |
| `high_impact` | CR-5 (recommendation-impacting) | ⊆ 4 (P53-A: 4 rows w/ flag) |

Buckets are **deterministic partitions** of the proposal set by the rule that
routed the row; a row may sit in `high_impact` AND its base bucket.

## 2. Proposal record (flat contract, reuse P53-A convention)

Every item entering review carries:
`entity_id, entity_name, field, axis, current_value, proposed_value,
basis, confidence_before, confidence_after, evidence_refs[],
review_bucket, high_impact, source_disagreement, recommendation_impact, reason`.
(Mirrors `conflict_priority_queue.csv` columns + proposal fields; no new schema.)

## 3. Assignment workflow (deterministic, no AI)

1. **Aggregate** — collect proposals from all five policies into one set.
2. **Partition** — tag `review_bucket` per §1; flag `high_impact`.
3. **Order** — within bucket, sort by P53-A `priority_score` desc, then
   `entity_id` lexicographic (reproducible; ties broken deterministically).
4. **Assign reviewer** — round-robin across the human reviewer pool keyed by
   `hash(entity_id) mod pool_size` (deterministic; no inference).
5. **Review** — reviewer decides **APPROVE / REJECT / REQUEST-SOURCE** using the
   evidence refs; decision logged with `review_status` + `reason`.
6. **Route outcome:**
   - APPROVE → proposal enters the **approved proposal set** (handed to the
     downstream apply gate; Workstream C does NOT write production).
   - REJECT → logged to `review_conflict_log` (already present in
     `integrity_baseline.json`), quarantined, not written.
   - REQUEST-SOURCE → returns to `missing`/`lowconf` bucket for re-run when a
     source arrives.

## 4. Determinism & integrity

- Same proposal set ⇒ identical buckets, order, assignments (no RNG, no clock in
  routing logic).
- The P53-A `integrity_baseline.json` is the tamper guard: the apply gate (outside
  C) must reproduce baseline hashes before committing any approved proposal.
- AOUS-reusable: the bucket/order/assign logic is pure function of the proposal
  records — an AOUS agent can run it without code.

## 5. Reporting

- Emit `workstream_c_review_queue.csv` (staging/report only) + a summary matching
  the P53-A `review_statistics.md` style (queue size, by bucket, by axis,
  approved/rejected counts). Production untouched.

## Definition of Done

- [x] 5 review buckets mapped to the policies; deterministic partition.
- [x] Proposal record reuses P53-A column convention; no new schema.
- [x] Deterministic ordering + round-robin assignment (no AI).
- [x] Outcome routing (approve→apply gate / reject→log / request-source→re-bucket).
- [x] Integrity-baseline guard referenced; no production write.

## Ad-hoc verification

See combined verification in delivery message.
