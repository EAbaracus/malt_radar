# P203 — Alias / Mismatch Grouping

## Mismatch categories detected (counts across all representations)
| mismatch type | count | example trigger |
|---|---|---|
| distillery-suffix | 438 | '… Distillery' |
| unicode | 219 | accented chars |
| punctuation | 159 | . , & / |
| owner-suffix | 63 | '… Co.' |
| the-prefix | 51 | 'The Macallan' |
| apostrophe | 42 | 'Jack Daniel's' |
| marketing-suffix | 27 | '… Estate/Reserve' |
| ltd-suffix | 24 | '… Ltd' |
| region-suffix | 11 | '… Speyside' |
| spacing | 1 | double spaces |

## Normalization pipeline (recommended, design only)
1. Unicode NFKC + strip accents.
2. Lowercase, trim.
3. Remove punctuation (`[^a-z0-9 ]`→space).
4. Tokenize; drop stop-words: the, distillery, distillers, ltd, limited, plc, co, company,
   speyside, islay, highland, lowland, campbeltown, ob, official, ib, independent, bottling,
   estate, reserve, single, malt, llc, gmbh, sa, spa.
5. Remaining tokens → canonical key (sorted or joined).
6. canonical key → entity_id (existing distillery_id or new).

## Worked example
`'The Macallan Distillery Ltd'` → tokens [macallan] → key `macallan` → entity_id (Macallan).
