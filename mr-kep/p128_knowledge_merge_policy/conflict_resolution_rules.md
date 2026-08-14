# P128 — Conflict Resolution Rules (READ-ONLY policy)

Arbitration rules for when book sources disagree, or when incoming book knowledge conflicts
with incumbent `production.db` values. Grounded in real tables: `review_conflict_log`,
`review_actions`, `review_status_transitions`, `staging_manual_review_queue`.
**Policy specification only — no writes.**

## Core doctrine (AGENTS.md)
- Never trust aggregate parser metrics alone; validate against source.
- When confidence low → **stop, explain, request verification** (route to review, never auto-pick).
- Last-writer-wins is **forbidden** for any REVIEW-REQUIRED field.

## Conflict types & arbitration

### 1. Numeric conflicts (age, abv, founded_year, coordinates)
| Field | Tolerance | Rule |
|---|---|---|
| abv | ±0.1% | within tolerance → keep incumbent, cite corroboration; beyond → REVIEW |
| age | exact | any mismatch → treat as **distinct expression**, not overwrite (see merge policy §3) |
| founded_year | exact | any mismatch → `review_conflict_log`, present all candidates, no auto-pick |
| coordinates | ~0.01° | beyond → REVIEW |

### 2. Categorical conflicts (region, type, status, country)
- **Rule:** if incoming authority > incumbent authority AND conf ≥ 0.90 → replaceable auto-apply.
- If authority equal or lower → REVIEW.
- `status` (active/closed/mothballed) → **always REVIEW** (temporal).

### 3. Textual/subjective conflicts (tasting notes, flavor descriptors)
- **Rule:** no conflict — both retained as additive evidence (append-only). Subjectivity is expected.
- Flavor **vector** divergence → resolved by knowledge.db consensus algorithm (`consensus_nodes`), not arbitration here.

### 4. Identity conflicts (from P127 AMBIGUOUS bucket, 3,556)
- Same alias → two entities: **REVIEW** (log in `review_conflict_log`, issue_type='identity_collision').
- Brand↔distillery ambiguity: **REVIEW**.
- Single-word/generic surface (conf 0.4): **REJECT** from promotion unless human confirms.

### 5. Source-authority ties
Tie-break order when two book sources are same tier & conf:
1. More recent edition wins for time-sensitive facts (status, ownership).
2. More specific source wins for domain facts (Yearbook for distilleries, Wishart/Classified for flavor).
3. If still tied → REVIEW.

## Authority tier table (incumbent vs incoming)
| Tier | Sources |
|---|---|
| T1 Official | distillery official site, official_source_references (official category) |
| T2 Reference | Malt Whisky Yearbook, World Atlas of Whisky, Michael Jackson, Whisky Classified, Flavour of Whisky |
| T3 General | Whiskypedia, Broom Manual, Complete Whiskey Course, Japanese Whisky guide |
| T4 Periodical | Whisky Advocate, Whisky Magazine, Scotch Whisky Annual |

**Overwrite permitted only when incoming tier ≤ incumbent tier number (i.e. ≥ authority) AND conf ≥ field threshold.**

## Conflict logging (design — where it WOULD be recorded at promotion time)
| Table | Purpose |
|---|---|
| `review_conflict_log` | one row per detected conflict (entity, field, incumbent, incoming, sources, resolution) |
| `staging_manual_review_queue` | REVIEW-REQUIRED items awaiting human decision |
| `review_actions` | recorded reviewer decisions |
| `review_status_transitions` | audit trail of status changes |
| `promotion_audit_log` | final promotion actions |

## Resolution decision flow
```
incoming field value
  ├─ field class IMMUTABLE?      → DISCARD (cite only)
  ├─ field class APPEND-ONLY?    → APPEND + citation
  ├─ field class REPLACEABLE?
  │     ├─ conf ≥ thr AND authority ≥ incumbent → APPLY + citation
  │     └─ else                                  → REVIEW
  └─ field class REVIEW-REQUIRED? → staging_manual_review_queue (always)
```

## Non-negotiables
- Price fields: never in conflict flow (never merged).
- `user_score`: never overwritten by any book source.
- Every applied change: mandatory citation row. No citation → no promotion.
