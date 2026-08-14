# Crawl Strategy — MR-KEP P62

Deterministic, polite, audit-friendly crawl plan. **No crawling is executed in
P62** — this defines the strategy for future Sprint 2+ extraction work.

## Principles

1. **Deterministic scope.** Each crawl is driven by a manifest
   (`mr-kep/manifests/*.yaml`) listing exact `source_key` + `scope`. Same
   manifest ⇒ same crawl set.
2. **Tier-aware intensity.** T1 official/reference first (slow, low volume);
   T2 structured next; T3 verification on-demand only.
3. **Respect robots + rate limits.** See `robots_policy.md`. No crawl without a
   prior robots check.
4. **Snapshot for provenance.** Every fetched page is archived (timestamped
   hash) so extractions are reproducible and auditable (evidence-first).
5. **Wayback fallback.** If a live page is unavailable/changed, fetch the
   nearest capture via Wayback CDX instead of guessing.

## Per-tier plan

| Tier | Mode | Cadence | Concurrency | Notes |
|------|------|---------|-------------|-------|
| T1 official | targeted per-brand | on new release / manual | 1 req / 5s | JS-heavy; may need static/JSON-LD parse |
| T1 reference | manual / none | edition-based | n/a | Books/PDFs: manual verification, not crawl |
| T2 expert (WhiskyFun) | blog + archive walk | periodic | 1 req / 3s | section-marker extraction (trigger_scan) |
| T2 structured (Whiskybase/retailers) | API/JSON-LD where permitted | periodic | 1 req / 2s | prefer structured endpoints over HTML scrape |
| T3 verification (Auctioneer/Wayback) | on-demand | per-conflict | 1 req / 3s | only when a claim needs anchoring |

## Matching before merge

Same-whisky resolution uses IoU ≥ 0.85 on
`[normalized_name, vintage, abv]` (see `HERMES.md` / `docs/merge_strategy.md`)
before any field merge — regardless of how many sources were crawled.

## Determinism safeguards

- Fixed `seed` per manifest.
- Content-addressed page snapshots (SHA-256) ⇒ re-crawl reproducibility.
- Retry history logged (max_attempts/backoff from source profile); retries
  never alter the logical result set.
- No random sampling for qualification — scope is explicit in the manifest.
