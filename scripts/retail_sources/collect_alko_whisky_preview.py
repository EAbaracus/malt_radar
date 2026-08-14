import json
import csv
import re
import os

RAW_FILE = 'data/output/retail/alko_50_raw.json'
OUT_CSV = 'data/output/retail/alko_whisky_preview.csv'

def extract_store_count(availability):
    if 'Available in' in availability and 'store' in availability:
        parts = availability.split('|')
        for p in parts:
            if 'store' in p:
                try:
                    num = int(''.join(filter(str.isdigit, p)))
                    return num
                except:
                    pass
    return 0

def main():
    print("Reading manually extracted MCP Playwright data (max 50)...")
    with open(RAW_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        
    start = content.find('### Result\n[') + 11
    end = content.find('\n### Ran Playwright code')
    if start < 11 or end == -1:
        print("Failed to find JSON block in raw file.")
        return
        
    json_str = content[start:end]
    data = json.loads(json_str)
    
    print(f"Loaded {len(data)} items from raw data.")
    
    out_rows = []
    seen = set()
    row_count_before = len(data)
    dup_dropped = 0

    for row in data:
        url = row['product_url']
        price = row['price'].replace(' €','').replace(',','.')
        size = row['bottle_size'].replace(' l','')
        abv = row['ABV']
        name_clean = row['product_name'].lower().strip()
        
        if url:
            dup_key = f"url:{url}"
        else:
            dup_key = f"name:{name_clean}|size:{size}|abv:{abv}|price:{price}"
            
        if dup_key in seen:
            dup_dropped += 1
            continue
        seen.add(dup_key)
        
        store_count = extract_store_count(row['availability'])
        online = 'Yes' if 'online shop' in row['availability'].lower() else 'No'
        
        out_rows.append({
            'source_system': 'alko.fi',
            'source_url': url,
            'product_name': row['product_name'],
            'category': row['category'],
            'country_region': row['country_region'],
            'price_eur': price,
            'bottle_size_l': size,
            'container_type': row['container_type'],
            'abv_percent': abv,
            'retail_style_label': '',
            'retail_descriptor_raw': '',
            'online_availability': online,
            'store_availability_count': store_count,
            'image_url': row['image_url'],
            'reviewer_decision': '',
            'reviewer_notes': ''
        })

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    with open(OUT_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=out_rows[0].keys())
        writer.writeheader()
        writer.writerows(out_rows)
        
    print(f"row_count_before_dedup: {row_count_before}")
    print(f"row_count_after_dedup: {len(out_rows)}")
    print(f"duplicate_rows_dropped: {dup_dropped}")
    
    dup_url_after = len([r for r in out_rows if r['source_url']]) - len(set([r['source_url'] for r in out_rows if r['source_url']]))
    dup_name_after = len(out_rows) - len(set([r['product_name'] for r in out_rows]))
    print(f"duplicate_product_url_count_after_dedup: {dup_url_after}")
    print(f"duplicate_product_name_count_after_dedup: {dup_name_after}")
    print(f"Wrote {len(out_rows)} items to {OUT_CSV}")

if __name__ == '__main__':
    main()
