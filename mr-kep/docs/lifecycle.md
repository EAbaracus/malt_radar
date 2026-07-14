# Lifecycle — MR-KEP

The end-to-end lifecycle of a single MR-KEP run, from manifest to gate.

## Phases

### 0. Manifest creation
- Copy `templates/manifest.yaml` → `manifests/<run>.yaml`.
- Pin `created_at`, `seed`, `sources`, and per-source `scope`.
- Validate against `schemas/manifest.schema.json`.

### 1. Qualification
- Agent: Qualification Agent.
- Reads source units per `source_profile.yaml` `qualification` rules.
- Emits `qualification.schema.json` record. No extraction.
- Checkpoint: qualification artifact + checksum.

### 2. Extraction
- Agent: Extraction Agent.
- For each in-scope unit, extract raw field values + verbatim `quote`.
- Emits `extraction.schema.json` records.
- Checkpoint: extraction artifact + checksum.

### 3. Validation
- Agent: Validation Agent.
- Normalize (per `field_rules.yaml`), score confidence (per `confidence.yaml`),
  reject authority-ceiling violations.
- Emits `normalization.schema.json` records.
- Checkpoint: validation artifact + checksum.

### 4. Merge
- Agent: Merge Agent.
- IoU-match units → same whisky (threshold 0.85).
- Resolve conflicts via `merge_policies.yaml`.
- Keep losing candidates as evidence; route unresolved to Audit.
- Checkpoint: merge artifact + checksum.

### 5. Certification
- Agent: Certification Agent.
- Attach `evidence.schema.json` per field; enforce `certify_min` (0.70).
- Emit `certification.schema.json`; `audit_status = pending_audit`.
- **No production write.**
- Checkpoint: certification artifact + checksum.

### 6. Audit
- Agent: Audit Agent (read-only).
- Verify evidence; flag `confidence < 0.60`; resolve routed conflicts.
- Evaluate run gate: GO / PARTIAL_GO / NO_GO / AWAITING_APPROVAL.

### 7. (Future) Apply gate
- NOT part of Sprint 1. A separate, explicitly-approved gate performs the
  production write under backup + rollback.

## Checkpoint & resume

Each stage records `input_ref`, `output_ref`, `checksum` in the manifest. A
failed run resumes from the last passed stage using these checkpoints — no
re-extraction needed.

## Gate semantics

| Gate | Meaning |
|------|---------|
| GO | All certified facts valid; safe to promote later. |
| PARTIAL_GO | Some facts need manual review; rest promotable. |
| NO_GO | Row loss / fabrication / production mutation / unresolved identity conflict. |
| AWAITING_APPROVAL | Certification complete; human sign-off required before any apply. |
