# P203B — Statistics

| metric | value |
|---|---|
| self-alias rows (production) | 2144 |
| external resolved | 55 (15 data/books/new.csv + 40 mr-kep/p119_6) |
| external to review | 13 |
| total crosswalk | 2199 |
| total review | 13 |
| P202B resolved / review | 15 / 2 |
| FK bad | 0 |
| duplicate conflicts | 0 |

## Match method distribution
| method | count |
|---|---|
| exact | 2197 |
| normalized | 2 |

## Confidence distribution
- exact: 1.0 (production self-aliases + exact external hits)
- normalized: 0.9 (canonical-key match)
- ambiguous: 0.85 (rare; none observed this run)
- review queue: <0.7 (coverage-gap names)
