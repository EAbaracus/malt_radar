# Acquisition Priority (books NOT already in corpus)

Ranked by knowledge-pipeline value (factual/distillery directories = high; subjective tasting = medium). No auto-acquisition.

## Tier 1 — High reliability (factual metadata, distillery/region directories)

1. **Malt Whisky Yearbook 2020–2024** — annual distillery directory; extends B1. Reliability 5.
2. **The Distilleries of Scotland** — foundational distillery reference. Reliability 5.
3. **Charles MacLean — Scotch Whisky: A Liquid History** — authoritative history. Reliability 5.
4. **Scotch Whisky: From Region to Glass** (Dave Broom) — region/flavor methodology. Reliability 5.

## Tier 2 — Medium (educational / supplementary)

5. **Dave Broom — The Way of Whisky** (Japanese craft). Reliability 4.
6. **Ian Buxton — 101 Whiskies to Try Before You Die** — consumer guide. Reliability 3.
7. **Stefan Van Eycken — Whisky Japan** — region deep-dive. Reliability 4.

## Tier 3 — Already partially present, register & dedupe first

8. **Whisky Advocate Archive** — register existing issues (currently UNREGISTERED) + dedupe overlaps.
9. **Whiskypedia** — resolve EN/RU translation pair.

## Action before acquisition

- Refresh `book_registry.json` (re-hash `data/books/` so UNREGISTERED books get records).
- Run dedupe pass on Whisky Advocate / Whiskypedia.
- Then stage Tier-1 acquisitions.
