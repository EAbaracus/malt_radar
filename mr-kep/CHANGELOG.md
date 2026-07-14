# CHANGELOG — MR-KEP

All notable changes to MR-KEP are documented here. Format: keep-a-changelog
(Added / Changed / Removed / Fixed). Versioning follows the pipeline's
schema_version (`MAJOR.MINOR.PATCH`).

## [1.0.0] — Sprint 1 (FOUNDATION)
**Status:** Released (standards + skeleton only).

### Added
- Repository skeleton: `authority/`, `schemas/`, `manifests/`, `templates/`,
  `pipelines/`, `sources/`, `examples/`, `docs/`.
- Top-level docs: `README.md`, `AGENTS.md`, `HERMES.md`, `MERGE_STRATEGIES.md`,
  `CHANGELOG.md`, `ROADMAP.md`.
- Authority layer (5 files): `authority_matrix.yaml`, `source_priority.yaml`,
  `field_rules.yaml`, `confidence.yaml`, `merge_policies.yaml`.
- JSON Schemas (6 files): `manifest`, `qualification`, `extraction`,
  `normalization`, `certification`, `evidence`.
- Templates (4 files): `manifest.yaml`, `source_profile.yaml`,
  `merge_strategy.yaml`, `certification.yaml`.
- Docs (5 files): `architecture.md`, `lifecycle.md`, `authority_model.md`,
  `merge_strategy.md`, `glossary.md`.
- First source profile: `sources/whiskyfun/source_profile.yaml`.
- Six agent roles defined in `AGENTS.md` (Qualification, Extraction, Validation,
  Merge, Certification, Audit).

### Changed
- Nothing (initial foundation).

### Removed
- Nothing.

### Fixed
- Nothing.

---
*No scraper, parser, or extraction code was written in Sprint 1, by design.*
