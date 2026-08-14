# P245C-6 — Residual JSON Classification Cleanup (READ-ONLY AUDIT)

**Mode:** audit only. No filter-repo. No delete. No commit. No push. No source change.

## Summary
- Reachable `*.json` blobs: **31**
- **KEEP: 21** (75 KB)
- **REMOVE: 10** (26 KB)

## Rules applied
- **KEEP:** `*.schema.json`, frontend/build manifests (`manifest.json`, `FontManifest.json`, `Contents.json`, `.mcp.json`), config/metadata (`source_metadata`, `field_rules`, `merge_policies`, `templates`).
- **REMOVE:** `*_stats.json` / `*_audit_stats.json`, `*_samples.json` / `*_sample*.json` (extraction examples w/ real records), capture-output JSON, large data dumps, JSON whose CONTENT contains real-record keys (`name`,`region`,`abv`,`distillery`,`whisky`,`flavor`,`tasting`, arrays of objects).
- **Borderline KEPT:** pipeline `*_manifest.json` (`capture_manifest`, `promotion_manifest`, `rollback_manifest`) — treat as config metadata per P245C-2 keep decision; flag for human review.

## REMOVE (RECOMMENDED) — 10 paths
- `mr-kep/p95b_fix03/canonical_profile_samples.json` — *_samples/_sample (extraction example w/ real records) (8KB)
- `mr-kep/p203c/capture_manifest.json` — capture output JSON (8KB)
- `mr-kep/p203c_retry/capture_manifest.json` — capture output JSON (5KB)
- `mr-kep/evidence_engine/examples/qualification_sample.json` — *_samples/_sample (extraction example w/ real records) (1KB)
- `mr-kep/p95b_fix03/canonical_profile_samples_extra.json` — content-real-records (1KB)
- `mr-kep/evidence/example_ledger_entry.json` — content-real-records (1KB)
- `mr-kep/structured_source_intake/htfw_audit_stats.json` — *_stats/_audit_stats (0KB)
- `mr-kep/structured_source_intake/vinmo_audit_stats.json` — *_stats/_audit_stats (0KB)
- `mr-kep/structured_source_intake/alko_audit_stats.json` — *_stats/_audit_stats (0KB)
- `mr-kep/structured_source_intake/notes_audit_stats.json` — *_stats/_audit_stats (0KB)

## KEEP — 21 paths
- `mr-kep/p403_books_promotion_readiness/06_promotion_manifest.json` — pipeline manifest (borderline->keep) (27KB)
- `mr-kep/evidence/evidence_schema.json` — schema (6KB)
- `mr-kep/extraction/canonical_output.schema.json` — schema (6KB)
- `mr-kep/editorial/schema/editorial_review.schema.json` — schema (5KB)
- `mr-kep/p203c/robots_report.json` — report (non-data) (5KB)
- `mr-kep/source_intake/source_metadata.json` — config/metadata (3KB)
- `mr-kep/p403_books_promotion_readiness/07_rollback_manifest.json` — pipeline manifest (borderline->keep) (2KB)
- `mr-kep/schemas/manifest.schema.json` — schema (2KB)
- `frontend/ios/Runner/Assets.xcassets/AppIcon.appiconset/Contents.json` — frontend/build manifest (2KB)
- `mr-kep/schemas/evidence.schema.json` — schema (2KB)
- `mr-kep/schemas/extraction.schema.json` — schema (2KB)
- `mr-kep/schemas/certification.schema.json` — schema (1KB)
- `mr-kep/schemas/qualification.schema.json` — schema (1KB)
- `mr-kep/schemas/normalization.schema.json` — schema (1KB)
- `frontend/web/manifest.json` — frontend/build manifest (0KB)
- `mr-kep/p137b_smws_promotion/promotion_manifest.json` — pipeline manifest (borderline->keep) (0KB)
- `mr-kep/examples/evidence_record_example.json` — content-non-data (0KB)
- `frontend/ios/Runner/Assets.xcassets/LaunchImage.imageset/Contents.json` — frontend/build manifest (0KB)
- `build/flutter_assets/FontManifest.json` — frontend/build manifest (0KB)
- `build/flutter_assets/NativeAssetsManifest.json` — frontend/build manifest (0KB)
- `.cursor/.mcp.json` — frontend/build manifest (0KB)

## STOP
No filter-repo run. If approved, a source-guarded `--paths-from-file=remove_candidates.txt` pass would apply this. Await human go.
