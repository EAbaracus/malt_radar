# P203 — Mismatch Type Catalogue

Full taxonomy observed in the data (matches the spec's example list + extras found):

| type | observed | fix |
|---|---|---|
| spacing | yes | collapse whitespace |
| punctuation | yes (159) | strip `.,&/` |
| the-prefix | yes (51) | drop leading 'The' |
| ltd-suffix | yes (24) | drop Ltd/Limited/PLC |
| ib-suffix | possible | drop Independent Bottling |
| region-suffix | yes (11) | drop Speyside/Islay/… |
| owner-suffix | yes (63) | drop Co./Company |
| marketing-suffix | yes (27) | drop Estate/Reserve/Single Malt |
| encoding | clean | NFKC; data is UTF-8 clean |
| unicode | yes (219) | NFKC + strip accents |
| apostrophes | yes (42) | normalize ' (Jack Daniel's) |
| abbreviations | yes | expand where mapped |
| legal-suffix | yes (LLC/GmbH/SA/SpA) | drop |

## Note
- Largest offender: **distillery-suffix (438)** and **unicode (219)** — these dominate noise.
- A single normalize+stopword pipeline resolves the overwhelming majority.
