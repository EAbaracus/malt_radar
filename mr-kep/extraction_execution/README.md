# README — MR-KEP Extraction Execution (`extraction_execution/`)

> **Phase P68 — Extraction Execution Planning.** Part of MR-KEP Sprint 1
> (frozen). This directory is **architecture/specification only** — it defines
> the deterministic lifecycle a *already-qualified* document follows from the
> Qualification Agent's verdict through to a Certification-Ready bundle.
>
> **NO implementation. No OCR. No parser. No scraper. No AI. No production
> interaction.** It references P62–P67; it does not modify them.

## Files

| File | Role |
|------|------|
| `README.md` | This index. |
| `execution_lifecycle.md` | Linear stage flow, checkpoints, evidence-emission timing, completion criteria. |
| `state_machine.md` | The 12 execution states + transitions, entry/exit, rollback point, evidence emitted, failure modes, retry policy. |
| `retry_and_recovery.md` | Deterministic retry constants + 7 failure classes + rollback rules. |
| `certification_handoff.md` | Certification entry requirements, handoff bundle contract, manual-review conditions. |
| `sprint1_readiness.md` | Definition of Done + GO/NO-GO + Sprint-1 phase readiness table. |

## Design posture

- Every state transition is a deterministic function of the previous state + the
  result of a deterministic check (gate / validation / checksum).
- Evidence is emitted **only** in the `Evidence Recording` state (P64 append-only
  ledger). No earlier stage writes evidence.
- Checkpoints = P65 bundles with SHA-256 checksums; resume from the last valid
  checkpoint (HERMES checkpoint system).
- Rollback never deletes or mutates the P64 ledger (immutability / append-only).
- Certification handoff never writes production; promotion is deferred to the
  explicit apply gate (Sprint 2).

## Compatibility

- Authority tiers / source classes → P63.
- Canonical output / bundles / validation → P65.
- Evidence ledger / hashes / audit rules → P64.
- Qualification gates / score → P67.
- Six-agent + pipeline vocabulary → Sprint 1 `AGENTS.md` / `pipelines/README.md`.
- AOUS-reusable: pure declarative contract, no code.
