# MR-KEP — Phase Archive Manifest

This directory archives historical non-execution phase documentation (preflight
audits, simulations, and dry runs) to keep the root domain workspace clean.

**Active canonical phases are in `ROADMAP.md` (root). This manifest is for
ARCHIVED / CLOSED phases only.**

---

## Archived Phases

| Phase ID | Status | Date | Scope | Closure Evidence | Historical Label | Archive Location |
|----------|--------|------|-------|-----------------|-----------------|-----------------|
| **P245C4** | CLOSED | 2026 | Non-execution — Removal Impact Audit | `06_final_verdict.md` | Non-execution (Removal Impact Audit) | `mr-kep/archive/p245c4_removal_impact/` |
| **P245C5** | CLOSED | 2026 | Non-execution — History Rewrite | `06_final_verdict.md` | Non-execution (History Rewrite) | `mr-kep/archive/p245c5_history_rewrite/` |
| **P245C6** | CLOSED | 2026 | Non-execution — JSON Cleanup Report | `json_cleanup_report.md` | Non-execution (JSON Cleanup Report) | `mr-kep/archive/p245c6_json_cleanup_report/` |
| **P251** | CLOSED | 2026 | Non-execution — Entity Binding Preflight | `06_final_verdict.md` | Non-execution (Entity Binding Preflight) | `mr-kep/archive/p251_entity_binding_apply_preflight/` |
| **P95B-Fix01** | CLOSED | 2026 | Non-execution — Reducer Contract Fix | `reducer_contract.md` | Non-execution (Reducer Contract Fix) | `mr-kep/archive/p95b_fix01/` |
| **P95B-Fix02** | CLOSED | 2026 | Non-execution — Regression Plan Fix | `implementation_plan.md` | Non-execution (Regression Plan Fix) | `mr-kep/archive/p95b_fix02/` |

---

## P500 Phase Summary (Canonical Pipeline)

The P500 phases are tracked in `ROADMAP.md` (root). Their closure evidence and
execution artifacts are in the repository history and closure reports. They are
**not moved to archive/** because they produced real code and production data.

| Phase ID | Status | Scope | Closure Evidence |
|----------|--------|-------|-----------------|
| P500-A | CLOSED | Architecture decision — MR-KEP + KEP Runtime canonical | ROADMAP.md Section 12 |
| P500-B | CLOSED | Canonical lifecycle model | ROADMAP.md Section 3 |
| P500-C | CLOSED | Canonical roadmap creation | ROADMAP.md (this file is the artifact) |
| P500-D | CLOSED | KEP Runtime ↔ MR-KEP integration | promotion_engine.py + editorial_promotion_writer.py wired |
| P500-E | CLOSED | Canonical PromotionGate | promotion_engine.py enforced as sole write path |
| P500-F | CLOSED | Canonical invariant registry | `mr-kep/common/invariant_registry.yaml` |
| P500-G | CLOSED | Feature branch → main merge | git log (commit 65b11dc) |
| P500-H | CLOSED | Real INGEST implementation | `mr-kep/acquisition/run_pipeline.py` |
| P500-I | CLOSED | Real EXTRACT implementation | `mr-kep/extraction_engine/extractor.py` |
| P500-J | CLOSED | P42 pending row resolution | Resolved via P500-O promotion |
| P500-K | CLOSED | NORMALIZE pipeline | `mr-kep/normalize/`, `d4_reducer/flavor_mapper.py` |
| P500-L | CLOSED | CANONICALIZE pipeline + knowledge.db revival | `mr-kep/canonicalize/` |
| P500-M | CLOSED | EVIDENCE pipeline | `mr-kep/evidence/` |
| P500-N | CLOSED | QA pre-promotion audit | staging_tasting_notes invariant pass |
| P500-O | CLOSED | Production promotion — 299 flavor_evidence via PromotionGate | SHA `40b7f71e...`, 3,180 flavor_evidence |
| P500-P | ACTIVE | Phase archive cleanup | This manifest |
| P500-Q | ACTIVE | Repository + documentation canonicalization | README, ROADMAP, AGENTS, CHANGELOG, ARCHITECTURE |

---

## Classic P32-P42 — RETIRED HISTORICAL APPENDIX

The classic pipeline (P32-P42) is **RETIRED and NOT CANONICAL**.
Entry point scripts were never committed. No revival planned.

These phases are NOT listed here as active items. They are referenced in
`ROADMAP.md` Section 11 (Classic P32-P42 — Retired Appendix) for historical
record only.

| Phase | Final State | Historical Data Location |
|-------|-------------|------------------------|
| P34A | FROZEN (retired), outputs exist | `output/p34/` |
| P36 | FROZEN (retired), outputs exist | `output/p36/` |
| P37 | FROZEN (retired), outputs exist | `output/p37/` |
| P38 | FROZEN (retired), outputs exist | `output/p38/` |
| P39 | FROZEN (retired), 733 rows staged | `staging_tasting_notes` in production.db |
| P40 | FROZEN (retired), NO GO | `output/p40/` |
| P41 | FROZEN (retired), READY_FOR_HUMAN_REVIEW | `output/p41/` |
| P42 | FROZEN (retired), AWAITING_PRODUCTION_APPROVAL | `output/p42/` |
| P44 | FROZEN (retired), GO | Similarity/KPI framework |
| P45-P49 | FROZEN (retired), GO | Similarity engine, optimization, release |

**Warning:** P39/P40/P41/P42 states were valid within the Classic pipeline
context only. They must NOT be interpreted as current canonical workflow states.
The staging data (733 rows) exists in production.db but the promotion path for
the remaining 72 rows is via KEP Runtime PromotionGate, not Classic pipeline.

---

## Archive Rules

1. Only non-execution phases (audits, preflights, simulations, dry-runs with no
   production mutation) go into `archive/`.
2. Execution phases with real production writes stay in root `mr-kep/` or are
   tracked in `ROADMAP.md`.
3. Every archived phase must have: Phase ID, Status, Closure Evidence, Historical Label.
4. No archived phase may appear as an active task in `ROADMAP.md`.
5. Archiving is one-way: archived phases are not un-archived.
