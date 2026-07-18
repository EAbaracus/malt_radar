# P203 — Inventory of Distillery Representations (READ ONLY)

> Distinct distillery representations found across all sources.

| source | distinct representations | notes |
|---|---|---|
| production.db (`whiskies.distillery_id` + `distilleries.name`) | 3130 | 986 distillery_id + 2,144 name values (dimension table exists) |
| knowledge.db | 0 | **0 distillery names** — no distillery dim in KB; source-of-truth is production |
| data/books/new.csv | 17 | free-text plain names (e.g. 'Glenlivet', 'Macallan') |
| existing staging CSVs (P119_6) | 51 | +51 names from prior P100-era staging |
| **TOTAL distinct (union)** | 3148 | union of all four |

## Key structural fact
- production.db has a real **`distilleries` dimension table** with columns:
  `distillery_id, name, country, region, owner, parent_company, founded_year, wikidata_id, data_confidence, …`
- External CSVs carry **free-text distillery names only** — no id, no country/region/owner.
- **This key-scheme mismatch is the root cause of P202B's 17 NO_MATCH rows.**
