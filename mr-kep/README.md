# MR-KEP — Malt Radar Knowledge Extraction Pipeline

> **Sprint 1 — FOUNDATION.** This sprint builds the *standards, schemas, and
> pipeline infrastructure* for MR-KEP. **No scraper, parser, or extraction code
> is written in this sprint.** The goal is a complete, deterministic, reusable
> repository skeleton that future AOUS agents consume to extract and certify
> whisky knowledge from external sources.

## What MR-KEP is

MR-KEP is the knowledge-extraction layer of Malt Radar. It takes external
reviews/sources (e.g. WhiskyFun) and produces **certified, evidence-backed
knowledge** that can later be promoted into the Malt Radar production database
under an explicit apply gate.

The pipeline has six deterministic stages, each owned by a dedicated agent:

```
qualification → extraction → validation → merge → certification → audit
```

Every fact that leaves the pipeline carries an **evidence record**
(provenance + confidence + authority tier) so nothing is fabricated and
everything is traceable.

## Directory layout

```
mr-kep/
├── authority/      # Authority layer: tiers, priorities, field rules, confidence, merge policies
├── schemas/        # JSON Schemas for every pipeline artifact (draft-07)
├── manifests/      # Concrete run manifests (instances of templates/manifest.yaml)
├── templates/      # Fill-in templates: manifest, source_profile, merge_strategy, certification
├── pipelines/      # Future: orchestration glue the AOUS agents execute (empty in Sprint 1)
├── sources/        # One folder per source; each has a source_profile.yaml (WhiskyFun first)
├── examples/       # Example artifacts demonstrating the schema contracts (added progressively)
└── docs/           # Architecture, lifecycle, authority model, merge strategy, glossary
```

## Guiding rules (non-negotiable)

- **Deterministic** — same inputs + same config ⇒ identical outputs. Fixed seed,
  no LLM-temperature-dependent logic in scoring.
- **Evidence-first** — no fact without a quoted source excerpt and a source URL.
- **Provenance tracking** — every value records where it came from and who won
  on conflict.
- **No fabrication** — if a source does not state a field, it stays empty; we
  never invent values to fill a schema.
- **Read-only verification** — this foundation reads standards only; production
  writes happen only on a later, explicit apply gate.

## Sprint 1 deliverables

See `docs/` and `ROADMAP.md` for the full plan. The Definition of Done is in
the sprint closing report (this sprint's delivery message).

## Repository compatibility

MR-KEP is designed to slot into the canonical Malt Radar pipeline without
re-architecture. Field names mirror the canonical model (`whiskies`,
`tasting_notes`, `flavor_profiles` 7-axis taxonomy: smoky, peaty, fruity,
sweet, spicy, maritime, sherry). Certified records are promotion-ready but are
**not** written to `production.db` by this sprint.
