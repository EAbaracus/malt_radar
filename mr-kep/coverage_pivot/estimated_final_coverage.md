# Estimated Final Coverage — Strategic Pivot Projection

**Baseline (post-S08):** 1,737 / 3,557 whisky_ids = **48.8%**
**Method:** READ-ONLY. New-coverage estimates derived from normalized matching of each remaining offline source against the production.db lexicon (name / original_name / distilleries / brands). Books probed live in Sprint 09. CSVs measured directly (see `coverage_strategy.md` §1).

> All figures are **estimates** (marked est.). "New whisky_ids" for CSV expression rows may be partly expression-variants of existing distilleries; a 50% realization factor is applied in the conservative column.

---

## Per-source new-coverage estimate

| Source | Raw new candidates | Conservative (50%) | Class |
|---|:-:|:-:|---|
| S2 Distilleries (215 raw) | 215 | ~215 | new distilleries (entity) |
| S1 Catalogue/expressions (313 raw) | 313 | ~160–313 | new expressions → whisky_ids |
| S3 Brands (116 raw) | 116 | ~116 | new brands (entity) |
| S10 B8 EPUB | 13 | 13 | new whisky_ids (book) |
| S4 HTFW | ~22 | ~10 | corroboration/identity |
| S5 SMWS | 0 | 0 | cask-scoped (no new id) |
| S9 Remaining books | ~0 | 0 | corroboration only |
| **Phase 1 + B8 total** | **~679** | **~514–667** | |

---

## Coverage projection (whisky_ids = expressions)

Current: **1,737** covered of 3,557.

| Scenario | New whisky_ids added | Projected coverage | % |
|---|:-:|:-:|:-:|
| **Optimistic** (S1 313 + S2 distilleries enable + S10 13 realized) | +~326 | ~2,063 | **58.0%** |
| **Conservative** (50% of S1 expressions + S2/S3 entity lift + B8) | +~200 | ~1,937 | **54.5%** |
| **Books-only (no pivot)** | +13 (B8 only) | 1,750 | **49.2%** |

**The pivot adds ~15–25× more coverage than continuing with books.**

---

## Entity-universe projection (whiskies + distilleries + brands)

| Entity | Current (est.) | + Phase 1 | Note |
|---|:-:|:-:|---|
| whiskies (expressions) | 3,557 | +~200–326 | primary coverage metric |
| distilleries | 1,913 | +~215 | S2 |
| brands | (in production) | +~116 | S3 |

---

## Verdict

- **Do NOT** process another corroboration book before exhausting Tier A CSV/export datasets.
- **Phase 1 (S2→S1→S3→S10)** is the highest-ROI sequence and can lift coverage from **48.8% → ~54–58%**.
- Recommended first sprint: **Step 1 = S2 Distilleries** (already staged, ~215 new, zero new extraction code).
- Tier B (SMWS/HTFW/Retail) then raises evidence quality on the enlarged base.
- Tier C (remaining books, Whiskybase sample, web) deferred — corroboration-only, minimal coverage value.

---

*Reproducibility: estimates computed read-only via normalized name match against production.db lexicon. Source files: `output/import/books/staging_*.csv`, `data/input/htfw_world_whisky_brands.csv`, `data/books/SMWS USA TASTING NOTES ARCHIVE/`, `data/books/The Complete Whisky Course -- Robin Robinson --.epub`. No DB modified.*
