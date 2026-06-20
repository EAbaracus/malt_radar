# Flavor Source Priority Policy

## 1. Overview
With the introduction of multiple flavor data sources (Existing Production, WhiskeyMapper, ScotchGit), a strict priority policy is required to ensure data integrity and prevent AI hallucinations from overwriting human-vetted data.

## 2. Source Priority Ranking
When a single `whisky_id` has flavor profiles from multiple sources, the app will resolve the effective profile using the following strict priority order:

1. **`production`** (Existing production data from `production_data.csv`)
   - **Confidence**: High (Human curated/vetted)
   - **Rule**: Never overwritten. Always wins.

2. **`whiskeymapper`** (Imported via WhiskeyMapper verification)
   - **Confidence**: Medium-High (From established external app)
   - **Rule**: Overwrites nothing. Wins if no `production` profile exists.

3. **`scotchgit`** (AI-extracted/generated from ScotchGit reviews)
   - **Confidence**: Low-Medium (AI extraction, prone to hallucination)
   - **Rule**: STRICT PREVIEW / QA ONLY. Never overwrites `production` or `whiskeymapper`.

4. **`unverified / ai_generated`**
   - **Confidence**: None
   - **Rule**: Excluded from app.

## 3. Data Integrity Rules
- **No Overwrites**: The `flavor_profiles` table must append rows for new sources, retaining the historical data. The `whiskies` table's materialized flavor data must only reflect the highest priority production-ready source.
- **Isolation**: `scotchgit` records must be isolated. In a production release, the app must behave as if `scotchgit` rows do not exist.

## 4. Conflict Resolution Strategy
- **no_conflict (74 rows)**: ScotchGit has data, Prod/WM do not. These are candidates for QA preview.
- **existing_production_profile (15 rows)**: ScotchGit has data, but Prod already exists. ScotchGit remains as a shadow record.
- **existing_production_profile|whiskeymapper_candidate (34 rows)**: ScotchGit has data, but both Prod and WM exist. ScotchGit remains as a shadow record.
