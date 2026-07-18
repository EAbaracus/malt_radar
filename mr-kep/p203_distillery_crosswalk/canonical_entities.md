# P203 — Canonical Entities (design)

> Grouping rule: normalize (lowercase, strip punctuation, remove stop-words/suffixes) → canonical key.
> Production `distilleries.distillery_id` is the preferred canonical anchor where a match exists.

## Example: Macallan family (verified in scan)
```
canonical_distillery = 'Macallan'   (distillery_id from production.distilleries)
aliases:
  - 'Macallan'
  - 'The Macallan'
  - (expected future) 'Macallan Distillery', 'Macallan (OB)', 'Macallan Speyside'
```

## Multi-representation groups discovered (sample of 112 found)

- `shizuoka` ← ['Shizuoka', 'Shizuoka Distillery']
- `lagavulin` ← ['Lagavulin', 'Lagavulin Distillery']
- `glenburgie` ← ['Glenburgie', 'Glenburgie Distillery']
- `hakushu` ← ['Hakushu', 'Hakushu Distillery']
- `kilbeggan` ← ['Kilbeggan', 'Kilbeggan Distillery']
- `virginia` ← ['Virginia Distillery Co.', 'Virginia Distillery Company']
- `teeling` ← ['Teeling', 'Teeling Distillery']
- `four roses` ← ['Four Roses', 'Four Roses Distillery', 'Four Roses Limited']
- `old grand dad` ← ['Old Grand-Dad', 'Old Grand-Dad Distillery']
- `midleton` ← ['Midleton', 'Midleton Distillery']
- `four gate` ← ['Four Gate', 'Four Gate The']
- `knob creek` ← ['Knob Creek', 'Knob Creek Single']
- `isle of jura` ← ['Isle of Jura', 'Isle of Jura Distillery']
- `rosebank` ← ['Rosebank', 'Rosebank Distillery']
- `benriach` ← ['BenRiach', 'Benriach', 'Benriach Distillery']
- `teeling whiskey` ← ['Teeling Whiskey Company', 'Teeling Whiskey Distillery']
- `aberfeldy` ← ['Aberfeldy', 'Aberfeldy Distillery']
- `cardrona` ← ['Cardrona Distillery', 'The Cardrona The']
- `waterford` ← ['Waterford', 'Waterford Distillery']
- `mars tsunuki` ← ['Mars Tsunuki', 'Mars Tsunuki The']
- `chita` ← ['Chita', 'Chita Distillery']
- `wild turkey` ← ['Wild Turkey', 'Wild Turkey Distillery']
- `amrut` ← ['Amrut', 'Amrut Distillery']
- `crown royal` ← ['Crown Royal', 'Crown Royal Single']
- `dingle whiskey` ← ['Dingle Whiskey Distillery', 'The Dingle Whiskey Distillery']

## Recommended canonical-entity rules
1. Prefer production `distilleries.distillery_id` as the canonical anchor (it carries region/owner/wikidata).
2. Where production has no entry (e.g. bourbon/blend brands), create a NEW canonical entity with a generated id.
3. Never mutate production to add aliases — keep aliases in the crosswalk table only.
