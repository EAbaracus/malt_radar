# P122 Phase 6 & 8 — Ingestion Value + Canonical Roadmap

Priority: CRITICAL/HIGH/MEDIUM/LOW. Driven by uniqueness, coverage gaps, evidence quality, resolver value — NOT popularity.

| Book | Plan | Ingestion Priority | Primary Contribution (knowledge, not row counts) |
|---|---|---|---|
| Koder-Scotch-Malt-Whisky-Society | - | CRITICAL | Overlapping/low net-new — ingest after canonical set. |
| Malt whisky yearbook 2019   the fa | B1 | CRITICAL | Structured distillery directory (founded/owner/capacity) → resolver entity backbone. |
| Japanese whisky   the ultimate gui | - | HIGH | Only JP reference → fills weak world-whisky subdomain. |
| The flavour of whisky | B5 | HIGH | 7-axis flavor methodology → canonical normalization authority for all flavor vectors. |
| The world atlas of whisky | B2 | HIGH | Regional structure + maps → region knowledge + distillery profiles. |
| The world guide to whisky michael  | B3 | HIGH | Foundational historical grounding → historiographic anchor. |
| Whisky classified ; choosing singl | B5 | HIGH | 7-axis flavor methodology → canonical normalization authority for all flavor vectors. |
| Charles, MacLean   John, MacPherso | - | MEDIUM | MacLean distillery history → narrative entity enrichment. |
| Jim Murray's Whisky Bible 2020   R | B4 | MEDIUM | Largest tasting-note corpus → dominant flavor-signal source. |
| The Complete Book of Whiskey: The  | B4b | MEDIUM | Encyclopedic global distillery coverage → broad entity resolution + flavor signals. |
| The Complete Whiskey Course | B8 | MEDIUM | Production + tasting course → resolver educational/processing facts. |
| Whisky  The First Definitive Book  | - | MEDIUM | 1930 historiographic primary → unique historical evidence. |
| Маклин, Чарльз - Whiskypedia  An I | - | MEDIUM | MacLean distillery history → narrative entity enrichment. |
| 50 - Whisky Advocate September 202 | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| A Field Guide to Whisky [eBook - B | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| A field guide the whisky | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| Dave Broom - Whisky  The Manual (2 | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| Lerner, Daniel - Single Malt and S | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| Malt whisky ; a contemporary guide | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| OceanofPDF.com Whisky Advocate - F | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| OceanofPDF.com Whisky Advocate - F | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| OceanofPDF.com Whisky Advocate - M | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| OceanofPDF.com Whisky Advocate - S | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| OceanofPDF.com Whisky Advocate - S | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| OceanofPDF.com Whisky Advocate - S | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| OceanofPDF.com Whisky Advocate - S | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| OceanofPDF.com Whisky Advocate - S | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| OceanofPDF.com Whisky Advocate - W | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| OceanofPDF.com Whisky Advocate - W | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| OceanofPDF.com Whisky Advocate - W | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| OceanofPDF.com Whisky Magazine - I | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| ScottishDistlleries.dbf | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| ScottishDistlleries.shp | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| ScottishDistlleries.shx | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| The Famous Grouse whisky companion | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| The Whisky Tasting Guide | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| The ultimate book of whiskey ; ove | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| Whiskey Opus | - | LOW | Photographic world survey → visual reference (low net-new vs Atlas). |
| Whisky Advocate - Wol  32 No  04 [ | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| Whisky Advocate December 2020 pdf | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| Whisky{Bruning, Ted}(2015, Bloomsb | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| [Scotch Whisky 2023-apr] - (2023)  | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| [Scotch Whisky The Whisky Magazine | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| [Scotch Whisky The Whisky Magazine | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| [Scotch Whisky The Whisky Magazine | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| annas-arch-21eb2f4fc714 | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| f59kpl16s2ge1.jpeg | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| let me tell you about whisky | - | LOW | Overlapping/low net-new — ingest after canonical set. |
| metadata.xml | - | LOW | Overlapping/low net-new — ingest after canonical set. |

## Recommended ingestion sequence (WHY)

1. **B1 Malt Whisky Yearbook (CRITICAL)** — factual distillery backbone; highest reliability (5); resolver entity seed.
2. **B6 SMWS Archive (CRITICAL)** — 792 staged vectors already extracted; exclusive cask evidence; promote after review gate.
3. **B5 Whisky Classified + Flavour of Whisky (HIGH)** — flavor-axis methodology; canonical normalization authority; unblocks all flavor vectors.
4. **B2 World Atlas + B3 Michael Jackson (HIGH)** — regional + historical structure; high reliability.
5. **Japanese Whisky (HIGH)** — fills weakest world-whisky subdomain; only dedicated JP ref.
6. **B4/B4b Jim Murray (MEDIUM)** — massive flavor signal but subjective (reliability 3); ingest after axis methodology (B5) to normalize.
7. **Whiskypedia / Aeneas MacDonald (MEDIUM)** — historical/narrative enrichment.
8. **LOW tier (Whisky Opus, Advocate, annuals, guides)** — overlapping/low net-new; ingest last or skip if redundant with above.