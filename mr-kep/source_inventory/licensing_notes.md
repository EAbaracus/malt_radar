# Licensing Notes — MR-KEP P62

Copyright / licensing risk assessment per source. **No content is copied or
redistributed in P62** — these notes govern future extraction + storage.

## Core licensing posture

1. **Facts are free; expression is protected.** Official specs (ABV, age,
   cask, region) are factual and usable. Tasting prose, scores, and images are
   copyrighted expression — store as **quoted evidence with attribution**, never
   verbatim republish.
2. **Quote, don't lift.** MR-KEP keeps `quote` excerpts (short, attributed) as
   provenance per `evidence.schema.json`. Full-article storage is out of scope.
3. **Images by reference only.** Bottle/label images are referenced by URL;
   never downloaded+redistributed. Copyright rests with the source.
4. **Price is internal-only.** Retail/auction prices are verification signals
   and **must never be exposed in UI/API** (Malt Radar product rule).

## Per-source licensing risk

| Source | Risk | Mitigation |
|--------|------|------------|
| Official Distillery Websites | Low (factual specs) / Med (images) | Use facts; images by URL; attribute |
| Scotch Whisky Association | Low | Quote definitions with attribution |
| World Atlas / Jackson / Broom | High (book copyright) | Manual verification reference; no automated extract; cite edition |
| WhiskyFun | Med (blog prose) | Short attributed quotes only; personal-use posture |
| Whisky Advocate | Med-High (subscriber + copyright) | Public reviews only; short quotes; attribute |
| Whiskybase | Med (DB ToS; no bulk redist) | API/ToS-compliant; attribution; no bulk export |
| Master of Malt / TWE | Med (retailer + image copyright) | JSON-LD facts; images by URL; price internal-only |
| Distiller magazines | Med-High | Public excerpts; attribute; no bulk |
| Whisky Auctioneer | Med (lot + image copyright) | Lot facts verified; images by URL |
| Wayback Machine | Low-Med | Respect original source's robots + copyright on replay |

## Red-line summary

- ❌ No verbatim republication of tasting notes / articles.
- ❌ No image redistribution.
- ❌ No price in UI/API.
- ❌ No bulk redistribution of structured DBs (Whiskybase) contrary to ToS.
- ✅ Factual specs + short attributed quotes + image URLs + internal price signals.

## Compliance record

Each future extraction run records, per source: license basis, attribution
string, and whether price (if any) is suppressed — stored in the run manifest
for audit.
