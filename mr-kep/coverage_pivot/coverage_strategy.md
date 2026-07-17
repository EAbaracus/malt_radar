# Coverage Strategy — Strategic Pivot (Post S08)

**Context:** Book enrichment S01–S08 complete. Coverage **1,737 / 3,557 whisky_ids (48.8%)**.
Remaining book corpus is saturated (Sprint 09 probe: every book adds ≈0 new whisky_ids; only B8 adds ~13).
**Decision:** Pivot from corroboration books to offline **structured datasets** (CSVs / exports / catalogs) which carry the real net-new coverage.

**This is a READ-ONLY analysis.** No source ingested. `knowledge.db` and `production.db` unmodified.

---

## 1. Full repository source audit (every remaining offline source)

| # | Source class | Physical location | Rows | Est. NEW whisky_ids | Corrob-only | Est. citations | Proc. cost | Confidence | Notes |
|---|---|---|:-:|:-:|:-:|:-:|:-:|:-:|---|
| S1 | **Catalogue / expressions (whiskynet.pl)** | `output/import/books/staging_catalogue.csv` (from `yeni veriler/catalogue.csv`) | 374 | **~313** | partial | high (per product) | Low (CSV, already staged) | High | 84% new; expression-level product list |
| S2 | **Distilleries (whiskynet.pl)** | `output/import/books/staging_distilleries.csv` | 351 | **~215** | partial | medium | Low | High | 62% new; distillery directory w/ owner/region/founded |
| S3 | **Brands (whiskynet.pl)** | `output/import/books/staging_brands.csv` | 263 | **~116** | partial | low | Low | High | 44% new; brand directory |
| S4 | HTFW world whisky brands | `data/input/htfw_world_whisky_brands.csv` | 276 | ~22 | yes | low | Low | High | mostly overlap w/ existing |
| S5 | SMWS USA Archive (803 cask notes) | `data/books/SMWS USA TASTING NOTES ARCHIVE/` + `output/import/smws/staging_smws_tasting_notes.csv` | 803 | **0 (cask-scoped)** | yes (cask) | very high | Very High | Med | flag `single_cask=1`; different table |
| S6 | Whiskybase export | `data/input/whiskybase_export_sample.csv` | 5 (sample) | 0 (sample) | yes | n/a | n/a | Low | **full export NOT in corpus** |
| S7 | Retailer (ALKO) | `data/output/retail/alko_whisky_preview.csv` | 50 (preview) | unknown | partial | low | Med | Low | price INTERNAL-only; full export not present |
| S8 | Low-risk web sources | `data/output/low_risk_sources/source_shortlist_v11.csv` | 8 (shortlist) | unknown | n/a | n/a | High (scrape) | Low | web, not local files |
| S9 | Books remaining (B5/B4/B7) | `data/books/` | ~1,300 pg | ~0 | yes | ~400 | Med | High | saturated (S09) |
| S10 | **B8 Robin Robinson EPUB** | `data/books/The Complete Whiskey Course -- Robin Robinson --.epub` | 22 docs | **~13** | yes | ~260 | Low | High | only book with net-new; T3 corroborate-only |
| S11 | Manual source collections | `data/manual_sources/` (review packs) | — | 0 | yes | n/a | n/a | High | these are *outputs* of prior reviews, not new sources |

> "Est. NEW whisky_ids" for S1–S3 measured by **normalized match** (lowercase + strip parentheticals + strip age + strip punctuation) of each name against the production.db lexicon (name/original_name/distilleries/brands, normalized). Conservative — some "new" expressions are variants of existing distilleries, but even at 50% realization this is **~320 net-new entities**, dwarfing all books combined.

---

## 2. Tier classification

### Tier A — Highest coverage gain (process FIRST)
| Source | Why A | Net-new potential |
|---|---|---|
| **S1 Catalogue/expressions** | 313 new product names, 84% not in production; directly adds expressions | ★★★ |
| **S2 Distilleries** | 215 new distilleries w/ structured metadata (owner/region/founded) | ★★★ |
| **S3 Brands** | 116 new brands | ★★☆ |
| **S10 B8 EPUB** | only book with net-new (+13), low cost | ★ (book) |

### Tier B — Highest evidence quality (process for consensus quality, not count)
| Source | Why B |
|---|---|
| **S5 SMWS (803 cask notes)** | first-party cask-level tasting → richest flavor signal; raises 7-axis consensus quality on known expressions (flag single_cask) |
| **S4 HTFW** | structured brand metadata (region/owner/founded) cross-validates identity fields |
| **S7 Retailer (ALKO)** | factual specs (abv/age/cask) verify official bottlings (price internal-only) |

### Tier C — Corroboration only (defer until A+B done)
| Source | Why C |
|---|---|
| **S9 Remaining books (B5/B4/B7)** | ≈0 new; pure corroboration — exactly the "Dave Broom Manual" pattern to avoid per S09 |
| **S6 Whiskybase sample** | only 5 rows; needs full member export to be useful |
| **S8 Low-risk web** | web scraping; not local; separate workstream |
| **S11 Manual collections** | review outputs, not sources |

---

## 3. Strategic principle

**Maximize total whisky coverage BEFORE returning to corroboration books.**
The book corpus cannot move coverage materially (ceiling ≈ +13). The CSV/export datasets (S1–S3) carry **~644 candidate new names** — the decisive lever. Process Tier A first (coverage), then Tier B (quality on the now-larger base), then Tier C (corroboration) last.

See `source_execution_order.md` for the sequence and `estimated_final_coverage.md` for the projection.
