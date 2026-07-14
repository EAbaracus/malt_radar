# pipelines/ — Orchestration (Sprint 1: empty by design)

This directory is reserved for the **orchestration glue** the AOUS agents
execute to run the MR-KEP stages end-to-end (qualification → extraction →
validation → merge → certification → audit).

**Sprint 1 is FOUNDATION** — no scraper, parser, or extraction code is written
this sprint, by design. The pipeline's *contracts* live in:

- `schemas/` — JSON Schemas every stage's artifact must satisfy.
- `authority/` — tiers, priorities, field rules, confidence, merge policies.
- `templates/` — fill-in manifests / source profiles / strategies.
- `manifests/` — concrete run instances (see `sprint1_foundation.yaml`).

When Sprint 2+ implements the agents, the per-stage driver scripts/modules
land here, each reading the matching schema + authority files and emitting a
checksummed, schema-validated artifact (see `docs/lifecycle.md` and
`HERMES.md` checkpoint system).
