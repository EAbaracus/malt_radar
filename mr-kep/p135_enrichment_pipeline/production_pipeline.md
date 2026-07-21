# P135 — Production Pipeline (Roadmap) (READ-ONLY Plan)

- doc_version: P135-1
- dependency graph. Only phases with measurable production value.

## Dependency graph
```
P134 (design, DONE)
  │
  ├─ D1: bootstrap target knowledge.db (canonical_vectors+citations+official_source_references)
  ├─ D2: uuid↔W crosswalk (SMWS backfill)  [P129 weak-only → strong]
  ├─ D3: official_source_references SMWS rows + source_citation_id on MERGE  [P128 C1]
  ├─ D4: schema fix (aroma_tags REAL→TEXT, drop foo, confirm axis scale)
  │
  ▼
P135 (this plan — ACCEPTED design)
  │
  ▼
P136 (Extraction/Normalization Engine — pure transforms, unit-testable, no DB)
  │   implements transformation_spec.md + normalization_rules.md
  ▼
P137 (Consensus Engine — field precedence + knowledge.db vector consensus)
  │   implements consensus_rules.md + conflict_policy.md
  ▼
P138 (Promotion Engine — dry-run diff → gated real write via P121)
  │   implements execution_batches.md + quality_gates.md
  ▼
P139 (QA — hash + count + FK + citation==change verification)
  │
  ▼
RELEASE (production metadata enriched)
```

## Phase value map
| phase | measurable production value | blocks |
|---|---|---|
| D1 | enables B4 vectors + all citations | B4, B3 citation |
| D2 | unblocks 443 MERGE vector promotion | B4 |
| D3 | satisfies P128 C1 (726 rows) | promotion gate |
| D4 | fixes aroma_tags/foo/scale bugs | clean schema |
| P136 | deterministic extract+normalize (reusable) | none |
| P137 | correct field precedence (no wrong overwrite) | none |
| P138 | actual metadata lift (cask_type +54pts etc.) | none (after D1–D4) |
| P139 | verified, reversible promotion | none |

## Recommended execution order (value-first)
1. **B1 SMWS tech** (no prereqs, +54pts cask_type) → immediate ROI.
2. **B2 SMWS notes** (no prereqs, +53pts nose/finish).
3. **D1+D3+D4** (enable citations + fix schema) → unblock gate.
4. **B3 books** (SEMI, +incremental).
5. **D2** (crosswalk backfill) → unblock B4.
6. **B4 vectors** (consensus).
7. **B5 knowledge** (descriptions).
8. **B6 recompute** (completed_fields 100%).

## What is explicitly OUT of scope (no value / forbidden)
- Identity resolution (task: complete, ignore).
- Price promotion (firewall).
- user_score overwrite.
- New entity creation (focus = enrichment of existing 4,749).
- Migrations to schema shape beyond D4 fixes.
