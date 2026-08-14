# Robots Policy — MR-KEP P62

Deterministic rules for robots.txt / crawl-permission compliance. **No crawling
executed in P62** — these are the binding constraints for future work.

## General rule

> **No source is crawled until its `robots.txt` is fetched and evaluated
> against the planned path + rate.** A blocking directive ⇒ the source is
> excluded from that crawl (downgraded to manual-verification only).

## Per-source robots stance (assessed, not fetched)

| Source | Expected robots posture | P62 stance |
|--------|-------------------------|------------|
| Official Distillery Websites | brand-specific; usually allows public pages | crawl only explicitly-allowed paths; respect Crawl-Delay |
| Scotch Whisky Association | public static; low risk | allowed; attribution |
| World Atlas / Jackson / Broom | print/PDF — not crawled | manual verification only; never automated |
| WhiskyFun | personal blog; allow with politeness | 1 req/3s; honor any Crawl-Delay; no archive abuse |
| Whisky Advocate | mixed; some subscriber content | crawl public reviews only; skip paywalled |
| Whiskybase | has API + ToS; bulk discouraged | prefer API; no bulk redist; attribution |
| Master of Malt / TWE | retailer ToS; crawl-delay common | use Product JSON-LD; respect Crawl-Delay |
| Distiller magazines | copyright; mixed | crawl public excerpts; attribution |
| Whisky Auctioneer | auction ToS | lot pages only; 1 req/3s |
| Wayback Machine | archive.org ToS; respect original robots | fetch via CDX; never bypass original block |

## Enforcement

- A `robots_check` step runs pre-crawl and records the evaluated directive +
  timestamp in the run manifest (evidence-first).
- If robots disallows a path mid-crawl, stop that path; do NOT retry with a
  different user-agent (no evasion).
- Violations are a hard **NO_GO** for the affected source.

## Rate limits (default)

- 1 request / 2–5s depending on tier (see `crawl_strategy.md`).
- Identified, honest User-Agent (`mr-kep/<version>` + contact).
- No parallel bursts; backoff on 429/503.
