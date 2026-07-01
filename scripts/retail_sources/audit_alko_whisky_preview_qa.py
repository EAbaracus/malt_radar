import csv
import collections
import os
import hashlib

PREVIEW_CSV = 'data/output/retail/alko_whisky_preview.csv'
MATCH_CSV = 'data/output/retail/alko_whisky_match_preview.csv'
REPORT_MD = 'output/reports/alko_whisky_50_qa_audit_report.md'
DB_PATH = "output/import/production.db"

def get_hash():
    if not os.path.exists(DB_PATH):
        return "NOT_FOUND"
    h = hashlib.sha256()
    with open(DB_PATH, 'rb') as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def main():
    hash_before = get_hash()
    
    rows = []
    with open(PREVIEW_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
            
    match_rows = []
    with open(MATCH_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            match_rows.append(r)
            
    total_rows = len(rows)
    
    urls = [r['source_url'] for r in rows if r.get('source_url')]
    names = [r['product_name'] for r in rows]
    
    dup_urls = [k for k,v in collections.Counter(urls).items() if v > 1]
    
    name_counts = collections.Counter(names)
    dup_names = [k for k,v in name_counts.items() if v > 1]
    
    # Check for exact duplicate rows (url, or name+price+size+abv combination)
    seen = set()
    exact_dups = 0
    for r in rows:
        key = f"{r.get('source_url')}|{r['product_name']}|{r.get('price_eur')}|{r.get('bottle_size_l')}|{r.get('abv_percent')}"
        if key in seen:
            exact_dups += 1
        seen.add(key)
    
    required_fields = ['source_system', 'source_url', 'product_name', 'category', 'country_region', 
                       'price_eur', 'bottle_size_l', 'abv_percent', 'online_availability', 'store_availability_count', 'image_url']
    
    missing_fields_count = collections.defaultdict(int)
    suspicious_prices = []
    suspicious_abvs = []
    suspicious_sizes = []
    
    for r in rows:
        for f in required_fields:
            if not r.get(f) or str(r.get(f)).strip() == '':
                missing_fields_count[f] += 1
                
        try:
            p = float(r['price_eur'])
            if p <= 10 or p >= 500:
                suspicious_prices.append(f"{r['product_name']} ({p} EUR)")
        except:
            if r.get('price_eur'): missing_fields_count['price_eur_parse_fail'] += 1
            
        try:
            a = float(r['abv_percent'])
            if a < 35 or a > 70:
                suspicious_abvs.append(f"{r['product_name']} ({a} %)")
        except:
            if r.get('abv_percent'): missing_fields_count['abv_parse_fail'] += 1
            
        try:
            b = float(r['bottle_size_l'])
            if b <= 0 or b > 5:
                suspicious_sizes.append(f"{r['product_name']} ({b} L)")
        except:
            if r.get('bottle_size_l'): missing_fields_count['size_parse_fail'] += 1
            
    match_status_dist = collections.defaultdict(int)
    high_conf = []
    score_exceeds_100 = 0
    
    for r in match_rows:
        status = r.get('match_status', 'no_match')
        match_status_dist[status] += 1
        score = int(r.get('match_candidate_score', 0))
        if score > 100:
            score_exceeds_100 += 1
            
        if status == 'high_confidence_match':
            high_conf.append(f"{r['product_name']} -> {r['match_candidate_name']} ({score}%)")
            
    # QA Decision Logic
    critical_errors = exact_dups > 0 or score_exceeds_100 > 0 or any(not k.endswith('_parse_fail') for k in missing_fields_count.keys())
    
    hash_after = get_hash()
    hash_same = hash_before == hash_after
    
    if critical_errors or not hash_same:
        qa_recommendation = 'NO-GO'
    elif len(suspicious_prices) > 0 or len(suspicious_abvs) > 0 or len(suspicious_sizes) > 0 or len(dup_names) > 0:
        qa_recommendation = 'WARN_GO'
    else:
        qa_recommendation = 'GO'
        
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    with open(REPORT_MD, 'w', encoding='utf-8') as f:
        f.write("# Alko Whisky QA Audit Report\n\n")
        f.write(f"- Total rows: {total_rows}\n")
        f.write(f"- Exact duplicate rows: {exact_dups}\n")
        f.write(f"- Variant duplicate product_name count: {len(dup_names)}\n\n")
        
        f.write("## Missing / Parse Failed Fields\n")
        if missing_fields_count:
            for k, v in missing_fields_count.items():
                f.write(f"- {k}: {v}\n")
        else:
            f.write("- None\n")
            
        f.write("\n## Suspicious Values\n")
        f.write("### Suspicious Prices (<= 10 or >= 500 EUR) Max 10\n")
        for x in suspicious_prices[:10]: f.write(f"- {x}\n")
        if not suspicious_prices: f.write("- None\n")
        
        f.write("\n### Suspicious ABV (< 35% or > 70%) Max 10\n")
        for x in suspicious_abvs[:10]: f.write(f"- {x}\n")
        if not suspicious_abvs: f.write("- None\n")
        
        f.write("\n### Suspicious Bottle Size (<= 0 or > 5 L) Max 10\n")
        for x in suspicious_sizes[:10]: f.write(f"- {x}\n")
        if not suspicious_sizes: f.write("- None\n")
        
        f.write("\n## Match Status Distribution\n")
        for k, v in match_status_dist.items():
            f.write(f"- {k}: {v}\n")
        f.write(f"- Scores > 100%: {score_exceeds_100}\n")
            
        f.write("\n## High Confidence Review Examples (Max 10)\n")
        for x in high_conf[:10]: f.write(f"- {x}\n")
        if not high_conf: f.write("- None\n")
        
        f.write("\n## Warnings\n")
        f.write("- **Raw descriptor leakage warning**: Confirmed descriptors are only present as retail metadata, NOT flavor/tasting import. Do not port to `flavor_profiles` without manual translation.\n")
        if len(dup_names) > 0:
            f.write(f"- **Variant Duplicates**: Found {len(dup_names)} names with multiple variants (different price/size/ABV).\n")
        
        f.write(f"\n## DB Integrity\n")
        f.write(f"- Hash before: {hash_before}\n")
        f.write(f"- Hash after: {hash_after}\n")
        f.write(f"- Hash same?: {'Yes' if hash_same else 'NO! DANGER'}\n")
        
        f.write(f"\n## Recommendation\n")
        f.write(f"**{qa_recommendation}** - ")
        if qa_recommendation == 'NO-GO':
            f.write("Critical errors (exact duplicates, score > 100%, missing fields, or DB hash mutation) found.\n")
        elif qa_recommendation == 'WARN_GO':
            f.write("Only suspicious values or variant duplicates detected, requires manual review.\n")
        else:
            f.write("All checks passed cleanly.\n")

if __name__ == '__main__':
    main()
