# 04 — Keep Guard Report (P245C-4)

Verifies KEEP candidates are NOT in the removal set.

| Category | Reachable count | In REMOVE set? |
|----------|-----------------|---------------|
| `*.schema.json` | 8 | NO ✅ |
| `*_manifest.json` | 8 | NO ✅ |
| source (.py/.dart/.sql/...) | 631 | NO ✅ |
| config (json/yaml/txt) | 6 | NO ✅ |

**GUARD PASSED:** No schema, manifest, source, or config file is in the removal set.

## Sample KEEP (schema) preserved
- `mr-kep/schemas/manifest.schema.json`
- `mr-kep/schemas/qualification.schema.json`
- `mr-kep/schemas/extraction.schema.json`
- `mr-kep/extraction/canonical_output.schema.json`
- `mr-kep/schemas/certification.schema.json`
- `mr-kep/schemas/evidence.schema.json`

## Sample KEEP (manifest) preserved
- `mr-kep/p403_books_promotion_readiness/06_promotion_manifest.json`
- `mr-kep/p403_books_promotion_readiness/07_rollback_manifest.json`
- `build/flutter_assets/NativeAssetsManifest.json`
- `mr-kep/p203c_retry/capture_manifest.json`
- `mr-kep/p137b_smws_promotion/promotion_manifest.json`
- `mr-kep/p203c/capture_manifest.json`
