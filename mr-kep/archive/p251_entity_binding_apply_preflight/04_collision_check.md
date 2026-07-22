# P251 — 04 — COLLISION CHECK (Wave C: NFKC normalization)

**Mode:** READ_ONLY · **Detects collisions introduced by ligature folding.**

## 1. What Wave C does

Folds Unicode ligatures (`ﬀ ﬁ ﬂ ﬁ ﬁ` → `ff fi fl ffi ffl`) then NFKC-normalizes the **name columns**
across `distilleries` (name), `whiskies` (name, original_name), `tasting_notes`
(normalized_name, source_name). This collapses import artifacts like `Glenﬁddich` → `Glenfiddich`.

## 2. Ligature footprint

- **55 name hits** contain ligatures across the 3 tables (Glenfiddich, Waterford Cuvée Kofﬁ,
  High West Campﬁre, Dogﬁsh Head, Litchﬁeld, Little Book the Inﬁnite, etc.).

## 3. Collision risk — REAL, must gate Wave C

Normalizing names can make **two genuinely distinct rows** collide on the now-identical normalized
name. The simulation found:

| Table | Within-table name collisions post-NFKC | Examples |
|-------|--------------------------------------:|----------|
| `distilleries` | **1** | `Glenfiddich` ← D0010 + D1091 (the intended merge) |
| `whiskies` | **13** | `glen scotia double cask`, `auchentoshan three wood`, `laphroaig quarter cask`, `ardbeg corryvreckan`, `amrut peated`, `forty creek resolve`, `glenrothes whisky maker's cut`, `paul john classic select cask`, … |
| **Total** | **~57** (across name/original_name/normalized_name/source_name columns) | — |

⚠️ **13 of these are `whiskies` rows that are NOT duplicates** — they are *different expressions*
that happen to share a normalized spelling (e.g. W000365 vs W002817 both named "glen scotia double
cask", likely different vintages/sources). Blindly overwriting names here would **merge distinct
entities' display identities** and break downstream dedup/UI.

## 4. Verdict on Wave C

- The **`distilleries` collision (Glenfiddich)** is *desired* — it is exactly the D1091→D0010
  canonicalization (Wave B) and is safe.
- The **`whiskies`/tasting_notes collisions are UNSAFE to auto-apply**: they would create false
  duplicate identities. Wave C name-normalization must be **scoped to `distilleries.name` only**
  (to support the merge) and, for `whiskies`/`tasting_notes`, limited to a **non-colliding
  subset** (rows whose normalized name is currently unique) with the 13 colliding pairs routed to
  **HUMAN_REVIEW**.

## 5. Safe Wave C subset

- ✅ `distilleries.name`: 1 hit (Glenfiddich) — fold, safe (merged away).
- ✅ `whiskies`/`tasting_notes` names whose normalized form is unique: 55 − (rows in colliding
  pairs) → apply.
- ❌ The ~13 colliding whisky pairs → **HUMAN_REVIEW** (do not auto-normalize; may need
  `original_name`/`age` disambiguation).

## 6. Conclusion

Wave C is **partially safe**: the `distilleries` fold is required and harmless; the `whiskies`/
`tasting_notes` fold must be collision-gated (unique-only auto-apply, colliding pairs to review).
This is the one wave that needs a human execution gate + collision exclusion list. No write.
