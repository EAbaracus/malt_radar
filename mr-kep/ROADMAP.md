# ROADMAP — MR-KEP

Phased plan for MR-KEP. Sprint 1 is FOUNDATION (this document's baseline).
Later sprints build on the standards defined here. Versions track
`schema_version`.

## Sprint 1 — FOUNDATION  ✅ (this sprint)
- Standards, schemas, authority layer, templates, docs, first source profile.
- No extraction code. Deterministic, evidence-first, read-only.
- **Exit:** complete repository skeleton; AOUS can read all contracts.

## Sprint 2 — Qualification + Extraction (planned)
- Implement Qualification Agent against `qualification.schema.json`.
- Implement Extraction Agent using declared `extraction_methods` for WhiskyFun.
- Emit extraction records with quoted provenance.
- **Precondition:** Sprint 1 contracts approved (gate GO).

## Sprint 3 — Validation + Normalization (planned)
- Implement Validation Agent: normalization per `field_rules.yaml`, confidence
  per `confidence.yaml`, authority-ceiling rejection.
- Emit normalized + validated records.

## Sprint 4 — Merge + Certification (planned)
- Implement Merge Agent using `merge_policies.yaml` + IoU matching.
- Implement Certification Agent: evidence records, `certify_min` enforcement.
- Emit certification records (staging evidence only; no production write).

## Sprint 5 — Audit + Apply Gate (planned)
- Implement Audit Agent: evidence verification, conflict routing, run gate.
- Define the explicit production apply gate (backup + rollback, mirroring
  Malt Radar P39/P42). Production write ONLY inside this gate.

## Future considerations
- Additional source profiles (beyond WhiskyFun).
- Multi-source consensus dashboards.
- Reuse of the authority layer by other Malt Radar ETL phases.

## Governance
- Each sprint ends with a GO / NO-GO gate.
- No production mutation without an explicit, separately-approved apply gate.
- Every deliverable verified read-only; failures reported, not hidden.
