# P405 — Promotion Commit & Release Record

**Release of the P403/P404 Books Promotion (human GO executed).**

## Promoted dataset
- Source staging: `staging_book_flavor_profiles`
- Target: `output/import/production.db` → table `flavor_evidence` (source='book')
- Manifest: `mr-kep/p403_books_promotion_readiness/06_promotion_manifest.json`

## Execution record (real apply, 2026-07-20)
| Metric | Value |
|---|---|
| Inserted | 58 |
| Updated | 8 (6 existing-row updates + 2 duplicate-collapses) |
| Skipped | 0 |
| Failed | 0 |
| Final book-source rows | 64 (exactly 1 per manifest whisky) |
| Duplicate book rows | 0 |
| Evidence total | 993 → 1049 |

## Integrity
| Item | Value |
|---|---|
| Pre-apply production.db SHA256 | `3c56de601c539260b49df57657eae4d47bfc8d0ebb27354b01c20648ac71656c` |
| Backup | `production.pre_p404_book_promo.20260720_131614.db` (sha `3c56de601c539260…`) |
| Post-apply production.db SHA256 | `9c3e1ba7d3e8911b50e9277ab175de774df0af696f8f4db815d7195b03db9b93` |
| Idempotent rerun | 0 inserted / 0 updated / 64 skipped → DB hash unchanged |
| Lossless rollback snapshot | `rollback_snapshot_book_rows.json` (8 original book rows retained) |

## Coverage impact
- 52 of 64 promoted rows are the whisky's FIRST evidence source.
- Whisky evidence coverage: **20.87% → 22.09%**.

## Excluded from VCS (per guardrails)
- `output/import/production.db` — git-ignored (`*.db`, `output/import/*.db`), never committed.
- `backups/` — git-ignored, never committed.
- No secrets, no APK, no build artifacts.

## Post-release state
- Branch: `feature/editorial-crawl-phase`
- Status: committed + pushed (this P405).
- Rollback remains available via `rollback_snapshot_book_rows.json` (lossless).

## Deliverables in this release (P403/P404 artifacts)
- `mr-kep/p403_books_promotion_readiness/` — 01–10 readiness + apply docs, manifests, snapshots
- `mr-kep/p403_books_promotion_readiness/06_real_apply_report.md` — real-apply report
- `mr-kep/authority/source_priority.yaml` — added `whiskymag` (SRC_013, T2_expert, priority 12) source tier

**P403/P404 BOOKS PROMOTION — RELEASED.**
