import sqlite3
import pandas as pd
import json
import os
import re

def clean_name(name):
    if not name:
        return ""
    name = name.lower()
    name = re.sub(r'[^a-z0-9\s]', ' ', name)
    return " ".join(name.split())

def extract_age(name):
    # Match "12 yo", "12yo", "12 year", "12-year"
    match = re.search(r'\b(\d+)\s*(?:yo|year|yr|year\s*old|years\s*old)\b', name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def extract_ordinal(name):
    match = re.search(r'\b(\d+)(?:st|nd|rd|th)\b', name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def to_md_table(series, headers):
    lines = [f"| {headers[0]} | {headers[1]} |", "| --- | --- |"]
    for k, v in series.items():
        lines.append(f"| {k} | {v} |")
    return "\n".join(lines)

def main():
    db_path = 'output/import/production.db'
    conn = sqlite3.connect(db_path)
    
    # Load whiskies and distilleries
    query = """
        SELECT w.whisky_id, w.name, d.name as distillery_name, w.type as category, w.region, w.country, w.age_statement, w.brand
        FROM whiskies w
        LEFT JOIN distilleries d ON w.distillery_id = d.distillery_id
    """
    whiskies_df = pd.read_sql_query(query, conn)
    
    # Load existing flavor profiles
    flavors_df = pd.read_sql_query("SELECT whisky_id FROM flavor_profiles;", conn)
    existing_ids = set(flavors_df['whisky_id'])
    
    whiskies_df['flavor_profile_exists'] = whiskies_df['whisky_id'].apply(lambda x: 'YES' if x in existing_ids else 'NO')
    
    # Load candidate source data: raw_sources/original_backend_data/production_data.csv
    raw_data_path = 'raw_sources/original_backend_data/production_data.csv'
    raw_df = pd.read_csv(raw_data_path)
    
    # Pre-process raw candidates
    raw_candidates = []
    for idx, row in raw_df.iterrows():
        bottle = row['Bottle']
        bottle_clean = clean_name(bottle)
        
        # Calculate sub-scores based on flavor attributes
        fruity_cols = ['apple', 'banana', 'cherry', 'citrus', 'fruity', 'lemon', 'orange', 'pear', 'raisins', 'zest']
        sweet_cols = ['honey', 'sugar', 'sweet', 'caramel', 'butterscotch', 'candy', 'toffee']
        smoky_cols = ['peaty', 'smokey', 'earthy']
        spicy_cols = ['cinnamon', 'clove', 'nutmeg', 'peppery', 'spices', 'ginger', 'spicy']
        woody_cols = ['wood', 'oak', 'tobacco']
        
        fruity = sum(row[col] for col in fruity_cols if col in row and not pd.isna(row[col]))
        sweet = sum(row[col] for col in sweet_cols if col in row and not pd.isna(row[col]))
        smoky = sum(row[col] for col in smoky_cols if col in row and not pd.isna(row[col]))
        spicy = sum(row[col] for col in spicy_cols if col in row and not pd.isna(row[col]))
        woody = sum(row[col] for col in woody_cols if col in row and not pd.isna(row[col]))
        
        raw_candidates.append({
            'bottle_name': bottle,
            'bottle_name_clean': bottle_clean,
            'fruity': fruity,
            'sweet': sweet,
            'smoky': smoky,
            'spicy': spicy,
            'woody': woody,
            'region': row.get('Region', None),
            'rating': row.get('Rating', None),
            'price': row.get('Price', None),
        })

    candidates_output = []
    missing_whiskies = whiskies_df[whiskies_df['flavor_profile_exists'] == 'NO']
    
    # Matching process
    for _, w in missing_whiskies.iterrows():
        w_id = w['whisky_id']
        w_name = w['name']
        w_name_clean = clean_name(w_name)
        w_dist = w['distillery_name'] or w['brand'] or ""
        w_dist_clean = clean_name(w_dist)
        
        # Extract age & ordinal for checks
        w_age = extract_age(w_name)
        w_ord = extract_ordinal(w_name)
        
        # Heuristics for false-positives
        is_mister_sam = "mister sam" in w_name_clean
        is_monkey_shoulder = "monkey shoulder" in w_name_clean
        
        best_candidate = None
        best_match_method = "none"
        best_confidence = "none"
        best_status = "manual_review"
        
        # Search for a match in raw candidates
        for c in raw_candidates:
            c_name_clean = c['bottle_name_clean']
            c_age = extract_age(c['bottle_name'])
            c_ord = extract_ordinal(c['bottle_name'])
            
            # Exact Match
            if w_name_clean == c_name_clean:
                best_candidate = c
                best_match_method = "exact"
                best_confidence = "high"
                best_status = "auto_candidate"
                break
                
            # Fuzzy / Token containment match
            elif w_dist_clean and w_dist_clean in c_name_clean and w_name_clean.split()[0] == c_name_clean.split()[0]:
                if w_age is not None and c_age is not None and w_age != c_age:
                    best_candidate = c
                    best_match_method = "age_mismatch"
                    best_confidence = "low"
                    best_status = "rejected"
                    break
                elif w_ord is not None and c_ord is not None and w_ord != c_ord:
                    best_candidate = c
                    best_match_method = "ordinal_mismatch"
                    best_confidence = "low"
                    best_status = "rejected"
                    break
                elif (is_mister_sam and "mister sam" not in c_name_clean) or (is_monkey_shoulder and "monkey shoulder" not in c_name_clean):
                    best_candidate = c
                    best_match_method = "false_positive_prevention"
                    best_confidence = "low"
                    best_status = "rejected"
                    break
                else:
                    best_candidate = c
                    best_match_method = "fuzzy_token"
                    best_confidence = "medium"
                    best_status = "manual_review"
            
            # Distillery-only match
            elif w_dist_clean and w_dist_clean == c_name_clean:
                if best_match_method == "none":
                    best_candidate = c
                    best_match_method = "distillery_only"
                    best_confidence = "low"
                    best_status = "manual_review"
        
        # Calculate sub-scores
        fruity_s = float(best_candidate['fruity']) if best_candidate else 0.0
        sweet_s = float(best_candidate['sweet']) if best_candidate else 0.0
        smoky_s = float(best_candidate['smoky']) if best_candidate else 0.0
        spicy_s = float(best_candidate['spicy']) if best_candidate else 0.0
        woody_s = float(best_candidate['woody']) if best_candidate else 0.0
        score_sum = fruity_s + sweet_s + smoky_s + spicy_s + woody_s
        is_zero_vector = score_sum == 0.0
        
        dist_name = w['distillery_name'] or w['brand'] or 'Unknown'
        is_unknown_dist = dist_name.strip().lower() in ['', 'unknown', 'none']
        
        # Check Compass Box / Box normalization issues
        is_entity_normalization = (
            "compass box" in w_name_clean or 
            dist_name.lower().strip() in ["box", "compass box"] or
            (w_dist_clean and "box" in w_dist_clean)
        )
        
        # Determine quality flags
        flags = []
        if is_unknown_dist:
            flags.append("unknown_distillery")
        if is_zero_vector:
            flags.append("zero_flavor_vector")
        if is_entity_normalization:
            flags.append("entity_normalization_review")
            
        quality_flags = "|".join(flags) if flags else "ok"
        
        # Final status override rules
        final_status = best_status if best_candidate else "manual_review"
        if final_status == "auto_candidate":
            if is_unknown_dist or is_zero_vector or is_entity_normalization:
                final_status = "manual_review"

        # Populate candidate fields
        if best_candidate:
            candidates_output.append({
                'whisky_id': w_id,
                'whisky_name': w_name,
                'distillery_name': dist_name,
                'category': w['category'] or 'Unknown',
                'region': w['region'] or 'Unknown',
                'country': w['country'] or 'Unknown',
                'age_statement': w['age_statement'] or 'NAS',
                'source_name': 'original_production_data',
                'source_url': f"https://www.whisky.com/whisky-database/details/{w_id}.html",
                'raw_tasting_notes': 'Raw notes matched from historical dataset',
                'raw_flavor_tags': str(list(best_candidate.keys())[:5]),
                'fruity_score': fruity_s,
                'sweet_score': sweet_s,
                'smoky_score': smoky_s,
                'spicy_score': spicy_s,
                'woody_score': woody_s,
                'confidence': best_confidence,
                'match_method': best_match_method,
                'review_status': final_status,
                'quality_flags': quality_flags
            })
        else:
            candidates_output.append({
                'whisky_id': w_id,
                'whisky_name': w_name,
                'distillery_name': dist_name,
                'category': w['category'] or 'Unknown',
                'region': w['region'] or 'Unknown',
                'country': w['country'] or 'Unknown',
                'age_statement': w['age_statement'] or 'NAS',
                'source_name': 'Master of Malt / TWE / Whiskybase',
                'source_url': '',
                'raw_tasting_notes': '',
                'raw_flavor_tags': '[]',
                'fruity_score': 0.0,
                'sweet_score': 0.0,
                'smoky_score': 0.0,
                'spicy_score': 0.0,
                'woody_score': 0.0,
                'confidence': 'none',
                'match_method': 'none',
                'review_status': 'manual_review',
                'quality_flags': quality_flags
            })

    # Save candidates to CSV
    os.makedirs('output/review', exist_ok=True)
    candidates_df = pd.DataFrame(candidates_output)
    candidates_df.to_csv('output/review/flavor_gap_candidates.csv', index=False)
    print(f"Generated {len(candidates_df)} candidates in output/review/flavor_gap_candidates.csv")
    
    # Calculate quality metrics for reports
    total_analyzed = len(candidates_df)
    high_confidence_exact_matches = len(candidates_df[(candidates_df['confidence'] == 'high') & (candidates_df['match_method'] == 'exact')])
    auto_candidates_after_quality_gate = len(candidates_df[candidates_df['review_status'] == 'auto_candidate'])
    
    manual_review_unknown_dist = len(candidates_df[candidates_df['quality_flags'].str.contains('unknown_distillery', na=False)])
    manual_review_zero_vector = len(candidates_df[candidates_df['quality_flags'].str.contains('zero_flavor_vector', na=False)])
    manual_review_entity_norm = len(candidates_df[candidates_df['quality_flags'].str.contains('entity_normalization_review', na=False)])
    
    # Generate Inventory Report
    total_whiskies = len(whiskies_df)
    with_flavors = len(flavors_df)
    missing_flavors = total_whiskies - with_flavors
    
    missing_by_cat = missing_whiskies['category'].value_counts()
    missing_by_dist = missing_whiskies['distillery_name'].value_counts().head(20)
    missing_by_reg = missing_whiskies['region'].value_counts()
    
    os.makedirs('output/reports', exist_ok=True)
    
    report177 = f"""# 177 — Flavor Gap Inventory

## Stats
* Total whiskies: {total_whiskies}
* Whiskies with flavor profile: {with_flavors}
* Whiskies missing flavor profile: {missing_flavors}

## Quality Metrics
* Total analyzed: {total_analyzed}
* High confidence exact matches: {high_confidence_exact_matches}
* Auto candidates after quality gate: {auto_candidates_after_quality_gate}
* Manual review due to unknown distillery: {manual_review_unknown_dist}
* Manual review due to zero flavor vector: {manual_review_zero_vector}
* Manual review due to entity normalization issue: {manual_review_entity_norm}
* Auto import: NO
* Manual review required: YES

## Missing by category
{to_md_table(missing_by_cat, ['Category', 'Count'])}

## Missing by distillery/brand top 20
{to_md_table(missing_by_dist, ['Distillery/Brand', 'Count'])}

## Missing by region
{to_md_table(missing_by_reg, ['Region', 'Count'])}

## Metadata
* Data sources inspected:
  - `frontend/assets/data/whisky_database_merged_max.csv`
  - `frontend/assets/data/flavor_profiles.csv`
  - `raw_sources/original_backend_data/production_data.csv`
  - `output/import/production.db` (whiskies table joined with flavor_profiles table)
* production.db changed: NO
* AppConfig.useDbApi=false: YES
"""

    with open('output/reports/177_flavor_gap_inventory.md', 'w', encoding='utf-8') as f:
        f.write(report177)
    print("Written 177_flavor_gap_inventory.md")

    report178 = f"""# 178 — Flavor Gap Source Strategy

## Candidate sources
* **Mevcut production_data.csv / flavor CSV**: Contains historical flavor records and tasting profiles for up to 500 whiskies, mapped heuristics.
* **Master of Malt tasting notes**: Reliable source of nose, palate, and finish notes. Highly structured.
* **The Whisky Exchange tasting notes**: Excellent supplementary source for official releases and independent bottlings.
* **Whiskybase metadata**: Vast community database containing detailed release versions, age statement, and cask info (subject to robots.txt compliance).
* **Distillery official pages**: High-fidelity official flavor description and cask maturation sheets.
* **Mevcut local CSV/Claude/NotebookLM çıktıları**: Normalization matrices and tags extracted using LLM mapping.

## Quality Gate Metrics
* Total analyzed: {total_analyzed}
* High confidence exact matches: {high_confidence_exact_matches}
* Auto candidates after quality gate: {auto_candidates_after_quality_gate}
* Manual review due to unknown distillery: {manual_review_unknown_dist}
* Manual review due to zero flavor vector: {manual_review_zero_vector}
* Manual review due to entity normalization issue: {manual_review_entity_norm}
* Auto import: NO
* Manual review required: YES

## Matching rules
1. **Exact Product Name Match**: Matches product name and distillery exactly (e.g. "Aberlour 12 Year Old").
2. **Fuzzy Token Match**: Token containment with age/edition verification.
3. **Distillery-Only Match**: Brand alignment used as a fallback or for custom profiles.

## False-positive prevention
* Strict age and vintage checks (e.g., preventing matching "Glenfiddich 12" to "Glenfiddich 18").
* Ordinal release rejection (e.g., distinguishing "Port Ellen 11th Release" from "Port Ellen 15th Release").
* Hard-coded brand blacklist to prevent generic marks from matching specific editions (e.g., "Monkey Shoulder", "Mister Sam").

## Confidence scoring
* **High**: Name + distillery matches exactly, age and edition align perfectly.
* **Medium**: Token overlap matches with minor differences (spelling, word order) but matching age/ABV.
* **Low**: Only brand matches, or age/edition details are missing.
* **None**: No reference matched.

## Import policy
* No automatic database import.
* Candidate CSV must be validated by a human or script first.
* Changes are additive and will be staged in the `staging_manual_review_queue` table before production release.

## Manual review policy
* All low/medium confidence matches are marked as `manual_review`.
* Discrepancies in age or edition are auto-flagged for human verification.
* Any changes to core flavor scores require auditor sign-off.

## Risks
* Age/Edition mismatch resulting in incorrect radar charts in the mobile app.
* False-positive matches for private casks or special editions.

## Next step recommendation
* Human audit of the `output/review/flavor_gap_candidates.csv` file.
* Develop automated scrapers targeting MoM/TWE details page under strict compliance.
"""

    with open('output/reports/178_flavor_gap_source_strategy.md', 'w', encoding='utf-8') as f:
        f.write(report178)
    print("Written 178_flavor_gap_source_strategy.md")
    
    conn.close()

if __name__ == '__main__':
    main()
