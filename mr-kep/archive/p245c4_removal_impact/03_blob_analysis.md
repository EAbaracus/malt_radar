# 03 — Blob Analysis (P245C-4)

- Distinct blobs to be removed: **8**
- Total byte-size affected (sum of max-version blob sizes): **15,036,545 bytes (15.04 MB)**
- This is 47368.1% of pack size (approx).

## Size breakdown by path

| Path | Distinct blobs | Max size (KB) |
|------|---------------|--------------|
| `artifacts/malt_radar_p6_snapshot.zip` | 1 | 14267 |
| `output/final/60_FINAL_import_ready_whiskies_distillery_patched.csv.bak_20260611002503` | 1 | 225 |
| `output/final/63_remaining_orphan_whiskies_after_patch.csv.bak_20260611002503` | 1 | 118 |
| `output/final/67_FINAL_import_ready_distilleries_whiskycom_enriched.csv.bak_20260611002503` | 1 | 61 |
| `output/orphan/bulk/08_orphan_bulk_high_confidence_patch.csv.bak_20260611002503` | 1 | 7 |
| `output/final/62_distillery_patch_diff.csv.bak_20260611002503` | 1 | 3 |
| `output/final/65_FINAL_IMPORT_FILE_MANIFEST.csv.bak_20260611002503` | 1 | 0 |
| `mr-kep/structured_source_intake/statistics.json` | 1 | 0 |

## Object-type note
All 8 targets are blobs (no trees/commits directly targeted). `git filter-repo`
will strip these blobs from every commit that references them, shrinking history
by ~15.0 MB.
