# P251 — 01 — APPLY SCOPE

**Mode:** READ_ONLY · **Dry-run only.** Final apply plan built from P248 (binding plan) + P249
(preflight) + P250 (namespace revalidation, MERGE_SAFE). No UPDATE/MERGE/DELETE/INSERT executed.

## 1. Frozen baseline

- `production.db` SHA (frozen at task start):
  `f341995184e883232e6993aa77ca103e2531d464a95d449c15a6ce857bf67a12`
- Opened exclusively `uri mode=ro`. No write handle taken.

## 2. Waves

| Wave | Action | Rows | Columns touched | Identity-safe? |
|------|--------|-----:|-----------------|:--------------:|
| **A** | AUTO_BIND NULL `distillery_id` (F7 695 + NULL-safe 1,207) | **1,902** | `distillery_id` (FK) | ✅ `whisky_id`/`name`/`age`/`abv` frozen |
| **B** | Canonicalize D1091→D0010, repoint children | 5 whiskies + 5 tasting_notes + 5 flavor_profiles | `distillery_id` | ✅ `whisky_id` frozen; **D0010 kept, D1091 deprecated** |
| **C** | NFKC ligature fold (`ﬁ`→`fi`, etc.) on name columns | 55 name hits across 3 tables | `name`/`original_name`/`normalized_name`/`source_name` | ⚠️ see collision risk §04 |

## 3. Scope boundaries (explicitly excluded, per P248/P249)

- ❌ Human-review rows (27 Rosebank + 724 NAS/ambiguous).
- ❌ The 14 P248 merge candidates (whisky-namespace merges) — separate track.
- ❌ 4 missing distilleries (St Magdalene, AnCnoc, Stronachie, Te Bheag) — require creation/alias.
- ❌ Any `whisky_id` reassignment or row deletion.

## 4. Target validity

- Wave A distinct targets: **215** `distillery_id`s — **all exist** in `distilleries` (0 invalid).
- Wave B survivor D0010 confirmed present (Speyside, Operating).
- Wave C normalization is column-local; no FK target changes.

## 5. Conclusion

Scope is fully enumerated and deterministic. 1,902 AUTO_BIND rows + 15 repoint rows + 55 name
normalizations are simulatable with no identity loss. Execution gate deferred to an authorized
task. No writes performed.
