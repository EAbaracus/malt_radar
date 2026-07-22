# 02 — Filter Execution (P245C-5)

```
git filter-repo --force --invert-paths \
  --paths-from-file=mr-kep/p245c3_hidden_data_audit/remove_candidates.txt
```

## Result
- Parsed **338** commits; rewrote history.
- New HEAD: `f9f6768` (`f9f67688d1704e1280c4a6f4674926fa74b8a478`)
- **8 blobs removed** (frozen removal set):

  - `artifacts/malt_radar_p6_snapshot.zip`
  - `output/final/60_FINAL_import_ready_whiskies_distillery_patched.csv.bak_20260611002503`
  - `output/final/63_remaining_orphan_whiskies_after_patch.csv.bak_20260611002503`
  - `output/final/67_FINAL_import_ready_distilleries_whiskycom_enriched.csv.bak_20260611002503`
  - `output/orphan/bulk/08_orphan_bulk_high_confidence_patch.csv.bak_20260611002503`
  - `output/final/62_distillery_patch_diff.csv.bak_20260611002503`
  - `output/final/65_FINAL_IMPORT_FILE_MANIFEST.csv.bak_20260611002503`
  - `mr-kep/structured_source_intake/statistics.json`

## Notes
- `--paths-from-file` (double-dash) used. Source-guard verified in P245C-4.
- No commit created; only historical blob references rewritten.
