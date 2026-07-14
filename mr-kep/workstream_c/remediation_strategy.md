# Workstream C — Remediation Strategy (Malt Radar Data Quality)

> **Assignment:** Workstream C only (Malt Radar Data Quality), under the MR-KEP
> three-workstream split. Builds on **P53 (Flavor Verification)** and **P53-A
> (Prioritization)**, which are COMPLETED and on disk.
>
> **Hard constraints (inherited from P53 brief + Sprint 1 freeze):**
> - **Objective is NOT to modify production data.**
> - Documentation / specification ONLY. No implementation. No production writes.
> - No schema changes. Reuse existing P53 / P53-A outputs.
> - Deterministic. Evidence-first. AOUS-reusable.

## 1. Source-of-truth inputs (reused, not redesigned)

| Artifact | Path | Shape reused |
|----------|------|--------------|
| P53 flavor ledger | `reports/p53/flavor_verification_ledger.csv` | `entity,entity_id,entity_name,field,current_value,verification_status,confidence,authority_source,provenance,last_verified,note` |
| P53 summary | `reports/p53/flavor_verification_summary.md` | headline metrics + confidence distribution (A/B/C/D/E/X) |
| P53-A priority queue | `reports/p53a/conflict_priority_queue.csv` | 1,443 rows; cols `priority_score,rank,entity_id,entity_name,field,axis,axis_weight,source_disagreement,confidence_gap,popularity_norm,popularity_coverage,recommendation_impact,current_value,authority_source,recommended_authority,manual_review_required,reason` |
| P53-A integrity baseline | `reports/p53a/integrity_baseline.json` | frozen `(row_count, sha256)` per production/staging table |
| P53-A review statistics | `reports/p53a/review_statistics.md` | queue size, axis/authority breakdown, score bands |

**Inventory (from P53 summary + P53-A statistics, verbatim):**
- Total prioritized records: **1,443** (`conflict_priority_queue.csv`, 1,444 lines incl. header).
- Flavor conflicts (confidence level **X**): **1,002**.
- Low-confidence flavor rows (level **E**, AI/rule-based enrichment): **441**.
- Missing flavor profiles: **375**.
- Tasting-note quality flags (generic/short): **912**.
- Authority mislabel: low-tier source labelled high ("source disagreements"): **319** (subset surfaced in the priority queue).

## 2. Remediation scope (what Workstream C covers)

Five defect classes, each mapped to a deliverable in this package:

| # | Defect class | Count | Input signal | Deliverable |
|---|--------------|:----:|--------------|-------------|
| R1 | Flavor **conflicts** (X) | 1,002 | P53 `confidence==X`; P53-A queue rows | `conflict_resolution_policy.md` |
| R2 | **Low-confidence** flavor profiles (E) | 441 | P53 `confidence==E` | `confidence_upgrade_strategy.md` |
| R3 | **Missing** flavor profiles | 375 | P53 "Missing flavor profiles" | `flavor_repair_workflow.md` |
| R4 | **Tasting-note** quality flags | 912 | P53 "Tasting-note flags" | `flavor_repair_workflow.md` |
| R5 | Authority mislabel (low tier → high) | 319 | P53-A `source_disagreement==1.0` rows | `conflict_resolution_policy.md` |

All counts are read-only facts from P53/P53-A; no re-computation required.

## 3. Architecture (three layers, all read-side)

```
            P53/P53-A artifacts (immutable inputs)
                         │
        ┌────────────────┼───────────────────────┐
        ▼                ▼                        ▼
  [Classifier]     [Confidence Model]      [Evidence Ledger]
  maps each row    upgrades E→A/B/C/D via    records every proposed
  to R1..R5 +      corroboration (reuse      change as an EVIDENCE
  disposition      P53 levels + P53-A        record (append-only),
                    axis_weight)              NEVER edits production
        │                │                        │
        └────────────────┼───────────────────────┘
                         ▼
              [Remediation Proposal Set]
     per-record: {entity_id, field, axis, current_value,
                  proposed_value, basis, confidence_after,
                  evidence_refs[], review_bucket, status}
                         │
                         ▼
              [Manual Review Pipeline]  ──→ human decision only
                         │
            ┌────────────┴─────────────┐
            ▼                          ▼
   APPROVED (staging/apply gate   REJECTED/QUARANTINED
   is a SEPARATE downstream       (logged, not written)
   action, NOT part of C spec)
```

- **No write path to `production.db`.** Approved proposals are handed to a
  downstream *apply gate* (out of Workstream C scope) that replays against the
  P53-A `integrity_baseline.json` before any commit. Workstream C emits
  **proposals + evidence**, never mutations.

## 4. Determinism & evidence-first invariants

- Every remediation proposal is a pure function of the P53/P53-A row + the fixed
  policy tables in this package. Same input row ⇒ same proposal (reproducible).
- Every proposal carries ≥1 `evidence_ref` pointing back to a P53 ledger row or a
  P53-A queue `reason`/`recommended_authority`. No value is asserted without a
  cited source.
- No inference / AI synthesis: "low-confidence" rows (E) are upgraded only by
  **corroboration with existing higher-authority sources already in the ledger**
  or by routing to human review — never by generating a new value.
- The P53-A `integrity_baseline.json` is the tamper-evident guard: any future
  apply step must reproduce those `(row_count, hash)` pairs for the tables it
  claims not to touch.

## 5. AOUS reusability

Each policy file is declarative (tables + decision rules), so an AOUS agent can
evaluate a row without code generation — exactly the pattern used across Sprint 1
(P62–P68) and P67. The proposal-set schema is a flat CSV/JSON contract compatible
with the existing `reports/p53a/` output convention.

## Definition of Done

- [x] Reuses P53 ledger + P53-A queue + integrity baseline as inputs (no redesign).
- [x] Five defect classes (R1–R5) mapped to the 5 deliverables.
- [x] Architecture has no production-write path; emits proposals + evidence only.
- [x] Determinism + evidence-first invariants stated.
- [x] Integrity-baseline guard referenced as the no-mutation control.
- [x] No implementation, no schema change, documentation only.

## Ad-hoc verification

See the combined verification block in the delivery message (PASS/FAIL).
