# P203C-RETRY — 06 Staging Report

Path: data/p203c_staging/editorial_staging_retry.db
Rows: 19 | distinct evidence_id: 19 (no dupes).
DDL corrected: index col -> canonical_distillery_id; added ingested_at; removed bad conflict clause.
Forbidden-name rows: 0. No raw HTML.

| source | raw_name | crosswalk | method | review | match | scale_max | excerpt(<=15w) |
|---|---|---|---|---|---|---|---|
| thewhiskyphiles | Glendronach Cask Strength Batch 12 | glendronach | exact | 0 | manual_review | 100.0 | ABV 58.2% Age NAS Bottler OB Cost £75  |
| thewhiskyphiles | SMWS 65.5 Old School Speyside | speyside | exact | 0 | unmatched | 100.0 | Imperial 21 Years Old 1995 65.5 Old Sc |
| thewhiskyphiles | Aberlour 9 Years Old Batch 7 | aberlour | exact | 0 | unmatched | 100.0 | ABV 49.6% Age 9 Years Old Bottler That |
| thewhiskyphiles | Millstone peated PX cask | — | — | 1 | unmatched | 100.0 | Millstone peated Pedro Ximénez sherry  |
| thewhiskyphiles | Deanston 14 Years Old Organic | deanston | exact | 0 | unmatched | 100.0 | Deanston 14 Years Old Organic Image co |
| thedramble | A Good Old Fashioned Christmas Whisky 20 | — | — | 1 | unmatched | None | A Good Old Fashioned Christmas Whisky  |
| thedramble | A Good Old Fashioned Christmas Whisky 20 | — | — | 1 | unmatched | None | A Good Old Fashioned Christmas Whisky  |
| thedramble | Black Friday 2023 Edition | — | — | 1 | unmatched | None | A Good Old Fashioned Christmas Whisky  |
| thedramble | Curraghmore Inaugural Release | — | — | 1 | unmatched | None | A Good Old Fashioned Christmas Whisky  |
| thedramble | Hollow tradition | — | — | 1 | unmatched | None | A Good Old Fashioned Christmas Whisky  |
| whiskynotes_be | 5 Decadent Drinks: Glenburgie, Clynelish | glenburgie | exact | 0 | unmatched | 100.0 | 17 July 2026 Ruben Ben Nevis , Blair A |
| whiskynotes_be | Mortlach / Dufftown / Oban (Casks of Dis | mortlach | exact | 0 | unmatched | 100.0 | 16 July 2026 Ruben Dufftown , Mortlach |
| whiskynotes_be | Speyside (M) 2009 – 100 Proof Exceptiona | speyside | exact | 0 | unmatched | None | 15 July 2026 Ruben Macallan Speyside ( |
| whiskynotes_be | Talisker 39 Years (G&M Connoisseurs Choi | talisker | exact | 0 | unmatched | None | 14 July 2026 Ruben Talisker Talisker 3 |
| whiskynotes_be | Kwun Cheung – Chinese single malt whisky | — | — | 1 | unmatched | 100.0 | 13 July 2026 Ruben * World Kwun Cheung |
| thewhiskeywash | Copperworks Farmsmith American Single Ma | — | — | 1 | unmatched | 10.0 | Copperworks Farmsmith American Single  |
| thewhiskeywash | Glenmorangie Harrison Ford Limited Editi | glenmorangie | exact | 0 | unmatched | 10.0 | Glenmorangie Harrison Ford Limited Edi |
| thewhiskeywash | Cedar Ridge The QuintEssential Solera Ed | cedar ridge the | exact | 0 | unmatched | 10.0 | Cedar Ridge The QuintEssential Solera  |
| thewhiskeywash | Kilchoman European Tour 2026 Edition Mez | kilchoman | exact | 0 | unmatched | 10.0 | Kilchoman European Tour 2026 Edition M |
