# Architecture — MR-KEP

How MR-KEP is structured and how it relates to the broader Malt Radar system.

## Layered design

```
┌─────────────────────────────────────────────────────────────┐
│                         AOUS (orchestrator)                  │
│  reads manifests/ + templates/ + authority/ to drive stages │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
  qualification → extraction → validation → merge → certification → audit
        │                                                              │
        ▼                                                              ▼
   sources/<key>/source_profile.yaml                        certification record
   (declarative metadata)                                   (staging evidence only)
                                                                        │
                                                                        │  (future explicit apply gate)
                                                                        ▼
                                                          Malt Radar production.db
                                                          (whiskies / tasting_notes /
                                                           flavor_profiles — 7-axis)
```

## Components

| Layer | Path | Role |
|-------|------|------|
| Authority | `authority/` | Tiers, priorities, field rules, confidence, merge policies |
| Schemas | `schemas/` | JSON Schema (draft-07) contracts for every artifact |
| Manifests | `manifests/` | Concrete run instances |
| Templates | `templates/` | Fill-in contracts (manifest, source_profile, merge_strategy, certification) |
| Pipelines | `pipelines/` | Future orchestration glue (empty in Sprint 1) |
| Sources | `sources/` | One folder per source; declarative `source_profile.yaml` |
| Examples | `examples/` | Example artifacts demonstrating the contracts |
| Docs | `docs/` | Human-readable design docs |

## Data flow contract

1. **Manifest** declares sources + stages + seed + gate.
2. **Qualification** reads `source_profile.yaml` scope → qualification record.
3. **Extraction** reads qualified units → extraction records (raw + quote).
4. **Validation** normalizes + scores → validated records.
5. **Merge** matches by IoU, resolves by policy → merged records.
6. **Certification** attaches evidence → certification record (no prod write).
7. **Audit** verifies + sets gate.

## Compatibility with Malt Radar

- Field names mirror the canonical model (`whiskies`, `tasting_notes`,
  `flavor_profiles`).
- Flavor taxonomy is the 7 canonical axes (smoky, peaty, fruity, sweet, spicy,
  maritime, sherry) — NOT the legacy 126-tag set.
- ABV normalization reuses the P53/P54 fix: strip `%` then `CAST REAL` (never
  `abv/100`).
- Production writes are deferred to an explicit apply gate, mirroring P39/P42's
  backup + rollback discipline. This foundation writes nothing to production.

## Determinism

Every artifact is content-addressed (SHA-256). Re-running with the same manifest
+ same source profiles yields identical artifacts. No hidden state, no network
non-determinism in scoring.
