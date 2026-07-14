# Example Resolution Flows — MR-KEP P63

> Spec only, deterministic, evidence-first, read-only. These are **illustrative
> planning flows** showing how the Source Resolution Engine would resolve fields
> for each entity type. No data is fetched; the source classes shown are the
> planned attempt order, not confirmed hits. Uses real-sounding examples for
> clarity only — no value is asserted as fact.

Legend for coverage_status: `COVERED_T1 / COVERED_T2 / COVERED_T3 /
PROPOSED_NEEDS_CERT / UNRESOLVED_CONFLICT / LOW_CONFIDENCE / UNCOVERED`.
Certification paths A–F are defined in `certification_paths.md`.

---

## 1. Distillery — e.g. "Glenfarclas distillery"

| Field | Preferred attempt | Coverage (planned) | Path | Result |
|-------|-------------------|--------------------|------|--------|
| distillery_name | official → regulatory | COVERED_T1 | A | CERTIFIED (identity, T1) |
| region | official → regulatory | COVERED_T1 + regulatory verify | B | CERTIFIED (corroborated) |
| abv (house style) | official → official_wayback | COVERED_T1 | A | CERTIFIED |
| nose/palate/finish | expert_review → book | COVERED_T2 | A | CERTIFIED (sensory, T2) |
| score | expert_review | COVERED_T2 | A | CERTIFIED |
| community_rating | community | COVERED_T3 | A | CERTIFIED (supporting only) |

Flow: T1 identity/official facts resolve directly; T2 sensory via expert review.
All ceilings satisfied → clean GO for this entity.

---

## 2. Brand — e.g. "Johnnie Walker" (spans sites)

| Field | Preferred attempt | Coverage (planned) | Path | Result |
|-------|-------------------|--------------------|------|--------|
| distillery_name | official → regulatory | COVERED_T1 | A | CERTIFIED (brand identity) |
| region | official → regulatory | PROPOSED_NEEDS_CERT (blend spans regions) | C | Region ambiguous → route to Certification |
| abv | official → official_wayback → regulatory | COVERED_T1 | A | CERTIFIED |
| flavor_axes | expert_review → book | COVERED_T2 (2 independent experts agree) | B | CERTIFIED (agreement bonus) |
| score | expert_review | COVERED_T2 | A | CERTIFIED |

Flow: brand identity may have an ambiguous single-region answer (a blend); the
resolver marks region PROPOSED_NEEDS_CERT rather than forcing one value.

---

## 3. Whisky — e.g. "Ardbeg Uigeadail" (product line)

| Field | Preferred attempt | Coverage (planned) | Path | Result |
|-------|-------------------|--------------------|------|--------|
| distillery_name | official → regulatory | COVERED_T1 | A | CERTIFIED |
| region | official → regulatory | COVERED_T1 | A | CERTIFIED |
| abv | official → official_wayback | COVERED_T1 | A | CERTIFIED |
| age_statement | official → structured_metadata | UNCOVERED (NAS product) | F | UNCOVERED (no age — not fabricated) |
| nose/palate/finish | expert_review → book | COVERED_T2 | A | CERTIFIED |
| score | expert_review | COVERED_T2 (2 experts, different dates) | latest_expert_wins | CERTIFIED (latest) |

Flow: NAS (no-age-statement) products yield UNCOVERED for age_statement — the
resolver reports the gap, never invents an age. Two dated expert scores resolve
by `latest_expert_wins`.

---

## 4. Independent Bottling — e.g. "Signatory Vintage Caol Ila 2010"

| Field | Preferred attempt | Coverage (planned) | Path | Result |
|-------|-------------------|--------------------|------|--------|
| distillery_name | official → regulatory | COVERED_T1 (distillery official) | A | CERTIFIED |
| abv | **official (bottler sheet)** → official_wayback → structured_metadata | COVERED_T1 (IB override order) | A | CERTIFIED |
| cask_type | official (bottler) → structured_metadata | COVERED_T1 | B | CERTIFIED (expert_review verify) |
| age_statement | official (bottler) → structured_metadata | COVERED_T1 | A | CERTIFIED |
| nose/palate/finish | expert_review → book | COVERED_T2 | A | CERTIFIED |

Flow: uses the **bottling override** — the bottler's own product data is the
`official` source; distillery official corroborates. `structured_metadata` is
promoted into the preferred order for IB official_bottling fields.

---

## 5. Closed Distillery — e.g. "Port Ellen" (silent)

| Field | Preferred attempt | Coverage (planned) | Path | Result |
|-------|-------------------|--------------------|------|--------|
| distillery_name | official → regulatory → **official_wayback → book** | COVERED_T1 (wayback) | A | CERTIFIED (archived official) |
| region | regulatory → official_wayback → book | COVERED_T1 | B | CERTIFIED (regulatory verify) |
| abv (of a specific release) | official_wayback → structured_metadata | PROPOSED_NEEDS_CERT | C | Route to Certification (no live official) |
| nose/palate/finish | expert_review → book | COVERED_T2 | A | CERTIFIED |
| score | expert_review | COVERED_T2 | A | CERTIFIED |
| age_statement | official_wayback → book | UNRESOLVED_CONFLICT (two archived pages differ) | D | Route to Certification |

Flow: uses the **distillery identity override** — `official_wayback` and `book`
carry identity because live official is gone. `wayback_required = true`. Two
archived pages disagreeing on age route to Certification (Path D), never
averaged.

---

# GO / NO-GO Criteria — P63

P63 is a **planning/spec** phase. GO means the resolution layer is complete,
deterministic, authority-consistent, and AOUS-ready — NOT that any data was
resolved.

## GO requires ALL of:
- [x] Source Resolution Model present (`source_resolution_model.yaml`) with
      entity_type, field_type, preferred_source_order, fallback_chain,
      verification_source, certification_source.
- [x] `source_resolution_matrix.csv` covers every (entity_type × field) cell
      (4 entities × 12 fields = 48 rows) with no gaps.
- [x] Coverage Resolver spec answers all 5 required questions (official,
      wayback, book, expert, structured metadata).
- [x] Resolution rules encode: official→direct, no-official→Tier2,
      conflict→certification, single→low-confidence, multi-independent→raise.
- [x] All 6 required outputs produced.
- [x] Example flows for all 5 entity types (distillery, brand, whisky, IB,
      closed distillery).
- [x] Every source class maps to a Sprint 1 authority tier (no invented trust).
- [x] Deterministic (ordered lists, priority tie-breaks, no randomness).
- [x] No scraper/parser/extractor/import/download code.
- [x] No production mutation; read-only.
- [x] No fabrication (UNCOVERED reported, never filled).

## NO-GO if ANY of:
- A matrix cell is missing or references an unknown source class/tier.
- A resolution rule is non-deterministic or averages conflicts.
- A T1-ceiling field can be certified by a T2/T3 source.
- Any scraper/parser/extractor/download code was written.
- Production data was read for mutation or written.
- A field with no coverage is filled with a fabricated value/source.

## Runtime GO/NO-GO (for a FUTURE resolved entity, defined here)
- **GO**: all identity fields COVERED_T1/certified; official_bottling either
  certified or explicitly UNCOVERED; ≥1 sensory or score certified.
- **PARTIAL_GO**: some fields PROPOSED_NEEDS_CERT / UNRESOLVED_CONFLICT /
  LOW_CONFIDENCE (manual review), rest certifiable.
- **NO_GO**: any **identity** field UNRESOLVED_CONFLICT, or a T1 field certified
  from a below-ceiling source, or fabrication detected.

---

# Definition of Done — P63

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Source Resolution Model (6 attributes) | ✅ |
| 2 | source_resolution_matrix.csv (48 cells) | ✅ |
| 3 | Coverage Resolver (5 signals) | ✅ |
| 4 | Resolution rules (5 rules) | ✅ |
| 5 | 6 required outputs produced | ✅ |
| 6 | 5 entity example flows | ✅ |
| 7 | GO/NO-GO criteria (phase + runtime) | ✅ |
| 8 | Built on P62/Sprint-1 authority layer | ✅ |
| 9 | AOUS-compatible (see below) | ✅ |
| 10 | Deterministic + evidence-first + no fabrication | ✅ |
| 11 | No scraper/parser/extractor/import code | ✅ |
| 12 | No production mutation (read-only) | ✅ |

---

# AOUS Compatibility Assessment — P63

The resolution layer is designed for direct AOUS consumption:

- **Declarative, machine-readable.** `source_resolution_model.yaml` and
  `source_resolution_matrix.csv` are structured artifacts an AOUS orchestrator
  reads to plan source attempts per (entity, field) — no code embedded.
- **Maps onto existing agents.** The plan feeds the Sprint 1 agents unchanged:
  Qualification (scope), Extraction (attempt order), Validation (authority
  ceiling), Merge (conflict routing), Certification (paths A–F), Audit (gate).
- **Single source of truth preserved.** All tiers/priorities/confidence/merge
  policies reference `mr-kep/authority/*`; P63 adds a *planning* layer without
  duplicating or overriding the authority layer.
- **Proposed additions are explicit.** New source classes (`reference_book`,
  `structured_metadata`) are recorded as `proposed_authority_additions` for a
  future, separately-approved authority update — P63 does not edit authority.
- **Deterministic + resumable.** Ordered lists + priority tie-breaks yield
  identical plans across runs, compatible with the checkpoint system in
  `HERMES.md`.
- **Read-only & no-write.** Nothing in P63 fetches, parses, or writes; the layer
  emits a *plan*, honoring the read-only-verification and no-fabrication rules.

**Verdict: AOUS-compatible.**
