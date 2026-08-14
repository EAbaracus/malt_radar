# P251 — 02 — FK BINDING SIMULATION (Wave A)

**Mode:** READ_ONLY · **In-memory dry-run.** 1,902 AUTO_BIND rows; only NULL `distillery_id` is set.

## 1. Method

For each row in scope, the target `distillery_id` is computed as a **deterministic function** of
immutable inputs (`staging_book_flavor_profiles.distillery_name` for F7; `whiskies.name` for
NULL-distillery, using **longest-match + canonical-preference on tie** per P250). No SQL write is
issued; the update set is tallied and asserted.

## 2. Results

| Sub-wave | Rows | Distinct targets | All targets valid? |
|----------|-----:|----------------:|:------------------:|
| F7 auto-bind (exact) | 695 | 33 | ✅ |
| NULL-distillery safe (longest-match, tie→canonical) | 1,207 | 215* | ✅ |
| **Total Wave A** | **1,902** | **215** | ✅ |

\* 215 = 33 (F7) ∪ 214 (NULL-safe). All 215 target `distillery_id`s exist in `distilleries`.

## 3. Identity preservation

| Column | Touched? | Rows changed |
|--------|:--------:|-------------:|
| `distillery_id` (FK) | ✅ | 1,902 |
| `whisky_id` (PK) | ❌ | 0 |
| `name` | ❌ | 0 |
| `age` / `age_statement` | ❌ | 0 |
| `abv` | ❌ | 0 |

Wave A is a **pure foreign-key population**. The whisky's identity (PK + name + specs) is untouched.

## 4. Idempotency

Target is a pure function of immutable inputs → re-applying yields **0 net changes** (updates only
NULL rows; once bound, a second pass matches 0 rows). ✅

## 5. Before / after

| Metric | Before | After (sim) |
|--------|-------:|------------:|
| `whiskies` NULL `distillery_id` | 1,931 | **724** |
| FK violations (populated id missing in `distilleries`) | 0 | 0 |

1,207 of the 1,931 NULL rows resolve; 724 remain (NAS/ambiguous/non-distillery-name → HUMAN_REVIEW,
out of scope).

## 6. Conclusion

Wave A is simulation-verified: 1,902 FK-valid, identity-preserving, idempotent bindings. No write.
