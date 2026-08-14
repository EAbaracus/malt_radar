import os
import csv
from collections import Counter

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "candidate_list.csv")
QUEUE_DIR = os.path.join(BASE_DIR, "candidate_queue")
TRACKING_CSV = os.path.join(BASE_DIR, "review_tracking.csv")
PROGRESS_MD = os.path.join(BASE_DIR, "population_progress.md")
STATS_MD = os.path.join(BASE_DIR, "population_statistics.md")
AUDIT_MD = os.path.join(BASE_DIR, "selection_audit.md")

os.makedirs(QUEUE_DIR, exist_ok=True)

MD_TEMPLATE = """# GSD Candidate: {canonical_name}
**Candidate ID:** {gsd_candidate_id}
**Status:** PENDING_REVIEW
**Benchmark Split Target:** {benchmark_split_target}
**Certification Tier Target:** {certification_tier_target}

> **INSTRUCTIONS:** Fill in the missing values. Every non-null field MUST have an evidence reference in Section 6. Missing evidence must NOT be guessed. 

## 1. Product Identity
- Canonical Name: {canonical_name}
- Display Name: {display_name}
- Distillery: {distillery}
- Brand: 
- Country: {country}
- Region: {region}
- Type: {type}
- Product Line: 
- Iconic Reason: {iconic_reason}

## 2. Official Authority (T1)
- Authority Tier:
- Authority Name:
- Authority Type:
- Official URL:
- Regulatory Classification:
- Appellation:
- Verified At:

## 3. Canonical Metadata
- ABV Percent: {approx_abv}
- ABV is Cask Strength: 
- Age Statement Years: {age_statement_years}
- Age Statement Raw:
- NAS: {nas}
- Vintage Year:
- Bottling Year:
- Cask Type: {cask_type_primary}
- Secondary Cask Type:
- Bottle Size (ml):
- Colorant Added:
- Chill Filtered:
- Limited Edition:

## 4. Flavor Profile (7-Axis)
- Smoky [0.0-10.0]:
- Peaty [0.0-10.0]:
- Fruity [0.0-10.0]:
- Sweet [0.0-10.0]:
- Spicy [0.0-10.0]:
- Maritime [0.0-10.0]:
- Sherry [0.0-10.0]:
- Dominant Axis:
- Axis Confidence:
- Flavor Source:
- Flavor Tags:
- Flavor Derivation Method:
- Axes Locked:

## 5. Tasting Notes
### Primary Note
- Reviewer:
- Review Date:
- Review URL:
- Score (0-100):
- Nose:
- Palate:
- Finish:
- Overall:

## 6. Evidence References
<!-- 
Provide evidence for every field. Format:
- Field: [field_name]
  Value: [value]
  Evidence Type: [primary_source_quote | bottle_print | expert_quote | aggregated_link]
  Authority Tier: [T1_authoritative | T2_expert | T3_community]
  Source URL: [url]
  Quote: "[exact excerpt]"
-->

## 7. Confidence & Certification
- Identity Confidence:
- Metadata Confidence:
- Flavor Confidence:
- Tasting Notes Confidence:
- Authority Confidence:
- Overall Confidence:
- Certification Gates (G1-G10) Passed:
"""

def generate():
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        candidates = list(reader)

    # 1. Generate Markdown files
    for i, row in enumerate(candidates, 1):
        filename = f"candidate_{i:04d}.md"
        filepath = os.path.join(QUEUE_DIR, filename)
        
        md_content = MD_TEMPLATE.format(
            gsd_candidate_id=row['gsd_candidate_id'],
            canonical_name=row['canonical_name'],
            display_name=row['display_name'],
            distillery=row['distillery'],
            country=row['country'],
            region=row['region'],
            type=row['type'],
            approx_abv=row['approx_abv'],
            age_statement_years=row['age_statement_years'] if row['nas'] == 'FALSE' else '',
            nas=row['nas'],
            cask_type_primary=row['cask_type_primary'],
            iconic_reason=row['iconic_reason'],
            benchmark_split_target=row['benchmark_split_target'],
            certification_tier_target=row['certification_tier_target']
        )
        
        with open(filepath, 'w', encoding='utf-8') as mf:
            mf.write(md_content)

    # 2. Generate tracking CSV
    with open(TRACKING_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['gsd_candidate_id', 'canonical_name', 'status', 'assigned_to', 'last_updated'])
        for row in candidates:
            writer.writerow([row['gsd_candidate_id'], row['canonical_name'], 'PENDING_REVIEW', 'UNASSIGNED', ''])

    # 3. Generate Progress MD
    with open(PROGRESS_MD, 'w', encoding='utf-8') as f:
        f.write("# Ground Truth Population Progress\n\n")
        f.write(f"- Total Candidates: {len(candidates)}\n")
        f.write("- CERTIFIED: 0\n")
        f.write("- VERIFIED: 0\n")
        f.write("- HOLD: 0\n")
        f.write(f"- PENDING_REVIEW: {len(candidates)}\n")

    # 4. Generate Statistics & Audit MD
    countries = Counter(c['country'] for c in candidates)
    regions = Counter(c['region'] for c in candidates)
    styles = Counter(c['type'] for c in candidates)
    peated = Counter(c['peated_level'] for c in candidates)
    
    with open(STATS_MD, 'w', encoding='utf-8') as f:
        f.write("# Population Statistics\n\n")
        f.write("## By Country\n")
        for k, v in countries.most_common():
            f.write(f"- {k}: {v}\n")
        f.write("\n## By Region (Scotland)\n")
        for k, v in regions.most_common():
            if k in ['Speyside', 'Islay', 'Highland', 'Lowland', 'Campbeltown', 'Islands']:
                f.write(f"- {k}: {v}\n")
        f.write("\n## By Style\n")
        for k, v in styles.most_common():
            f.write(f"- {k}: {v}\n")
        f.write("\n## By Peated Level\n")
        for k, v in peated.most_common():
            f.write(f"- {k}: {v}\n")

    with open(AUDIT_MD, 'w', encoding='utf-8') as f:
        f.write("# Selection Audit\n\n")
        f.write("## Rules Verification\n")
        
        scotland_pct = (countries.get('Scotland', 0) / len(candidates)) * 100
        f.write(f"1. **Max Scotland 40%**: {scotland_pct:.1f}% -> {'PASS' if scotland_pct <= 40.0 else 'FAIL'}\n")
        
        required_countries = ['Scotland', 'Japan', 'USA', 'Ireland', 'India', 'Canada', 'Taiwan']
        all_countries_present = all(countries.get(c, 0) > 0 for c in required_countries)
        f.write(f"2. **Cover all required countries**: {'PASS' if all_countries_present else 'FAIL'}\n")
        
        required_styles = ['Malt', 'Blend', 'Bourbon', 'Rye', 'Grain', 'Single Pot Still']
        all_styles_present = all(styles.get(s, 0) > 0 for s in required_styles)
        f.write(f"3. **Cover all required styles**: {'PASS' if all_styles_present else 'FAIL'}\n")
        
        required_regions = ['Speyside', 'Islay', 'Highland', 'Lowland', 'Campbeltown', 'Islands']
        all_regions_present = all(regions.get(r, 0) > 0 for r in required_regions)
        f.write(f"4. **Cover all required regions**: {'PASS' if all_regions_present else 'FAIL'}\n")
        
        peated_ok = peated.get('heavy', 0) > 0 and peated.get('none', 0) > 0
        f.write(f"5. **Include both peated and unpeated**: {'PASS' if peated_ok else 'FAIL'}\n")

if __name__ == '__main__':
    generate()
    print("Generation complete.")
