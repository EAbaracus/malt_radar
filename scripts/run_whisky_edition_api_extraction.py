import os
import sys
import json
import csv
import time
import requests
from pathlib import Path
try:
    from thefuzz import fuzz
except ImportError:
    fuzz = None

# Paths
BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "output" / "whisky_edition_api"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FINAL_DIR = BASE_DIR / "output" / "final"

API_BASE_URL = "https://thewhiskyedition.com"
API_LIST_ENDPOINT = "/api/whisky-reviews"

def resolve_openapi_path():
    candidates = [
        BASE_DIR / "backend" / "data" / "openapi.json",
        BASE_DIR / "openapi.json",
        Path("/mnt/data/openapi.json")
    ]
    for c in candidates:
        if c.exists():
            return c
    return None

def resolve_master_path():
    master_path = FINAL_DIR / "60_FINAL_import_ready_whiskies_distillery_patched.csv"
    if master_path.exists():
        return master_path
    
    manifest_path = FINAL_DIR / "65_FINAL_IMPORT_FILE_MANIFEST.csv"
    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("final_whisky_path") and Path(row["final_whisky_path"]).exists():
                    return Path(row["final_whisky_path"])
    return None

def clean_text(text):
    if text is None:
        return ""
    return str(text).strip()

def stage1_openapi_profile(openapi_path):
    print("--- Stage 1: OpenAPI Profile ---")
    if not openapi_path:
        print("OpenAPI file not found.")
        return
    with open(openapi_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    report_lines = ["# OpenAPI Profile Report", ""]
    endpoints = []
    if "paths" in data:
        for path, methods in data["paths"].items():
            for method, details in methods.items():
                desc = details.get("summary", details.get("description", ""))
                report_lines.append(f"{method.upper()} {path}: {desc}")
                endpoints.append({
                    "endpoint": path,
                    "method": method.upper(),
                    "description": desc
                })
    
    with open(OUTPUT_DIR / "01_openapi_profile_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    with open(OUTPUT_DIR / "02_endpoint_schema_summary.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["endpoint", "method", "description"])
        writer.writeheader()
        writer.writerows(endpoints)
    print("Stage 1 complete.")

def fetch_list_page(page, per_page):
    url = f"{API_BASE_URL}{API_LIST_ENDPOINT}?page={page}&per_page={per_page}"
    retries = 3
    delay = 10
    for attempt in range(retries):
        resp = requests.get(url, timeout=15)
        if resp.status_code == 429:
            print(f"429 Too Many Requests on page {page}, waiting {delay}s...")
            time.sleep(delay)
            delay *= 2
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()
    return resp.json()

def parse_list_item(item):
    meta = item.get("metadata", {})
    rating = item.get("rating", {})
    return {
        "id": item.get("id"),
        "slug": item.get("slug"),
        "lang": item.get("lang"),
        "name": clean_text(item.get("name")),
        "description": clean_text(item.get("description")),
        "url": item.get("url"),
        "pdf": item.get("pdf"),
        "published_at": item.get("published_at"),
        "authors": json.dumps(item.get("authors", [])),
        "type": meta.get("type"),
        "country": meta.get("country"),
        "region": meta.get("region"),
        "distillery": meta.get("distillery"),
        "bottler": meta.get("bottler"),
        "age": meta.get("age"),
        "abv": meta.get("abv"),
        "price_per_liter": meta.get("price_per_liter"),
        "flavour": meta.get("flavour"),
        "rating_marcel": rating.get("marcel"),
        "rating_sascha": rating.get("sascha"),
        "rating_value_for_money": rating.get("value_for_money"),
    }

def stage2_sample_fetch():
    print("--- Stage 2: Sample Fetch ---")
    data = fetch_list_page(1, 24)
    raw_file = OUTPUT_DIR / "03_sample_review_list_raw.json"
    with open(raw_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    items = data.get("items", [])
    parsed_items = [parse_list_item(item) for item in items]
    
    csv_file = OUTPUT_DIR / "04_sample_review_list_parsed.csv"
    if parsed_items:
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=parsed_items[0].keys())
            writer.writeheader()
            writer.writerows(parsed_items)
            
    with open(OUTPUT_DIR / "05_sample_fetch_report.txt", "w", encoding="utf-8") as f:
        f.write(f"Sample fetched: {len(parsed_items)} items.\n")
    print("Stage 2 complete.")
    return parsed_items

def fetch_detail(slug):
    url = f"{API_BASE_URL}{API_LIST_ENDPOINT}/{slug}"
    retries = 4
    delay = 10
    for attempt in range(retries):
        resp = requests.get(url, timeout=15)
        if resp.status_code == 429:
            print(f"429 Too Many Requests for {slug}, waiting {delay}s...")
            time.sleep(delay)
            delay *= 2
            continue
        resp.raise_for_status()
        return resp.json()
    resp.raise_for_status()
    return resp.json()

def extract_tasting_note(detail):
    item = detail.get("item", detail)
    t_notes = item.get("tasting_notes", {})
    conc = item.get("conclusion", {})
    return {
        "source_review_id": item.get("id"),
        "slug": item.get("slug"),
        "name": clean_text(item.get("name")),
        "nose": clean_text(t_notes.get("nose")),
        "palate": clean_text(t_notes.get("palate")),
        "finish": clean_text(t_notes.get("finish")),
        "conclusion_marcel": clean_text(conc.get("marcel")),
        "conclusion_sascha": clean_text(conc.get("sascha")),
        "source_url": item.get("url"),
        "source_api_endpoint": f"/api/whisky-reviews/{item.get('slug')}",
        "source_confidence": "high",
        "extraction_method": "api_json"
    }

def stage3_sample_detail_fetch(sample_items):
    print("--- Stage 3: Sample Detail Fetch ---")
    raw_lines = []
    tasting_notes = []
    for item in sample_items:
        slug = item["slug"]
        try:
            detail = fetch_detail(slug)
            raw_lines.append(json.dumps(detail))
            note = extract_tasting_note(detail)
            # Only add if at least one core tasting note exists
            if note["nose"] or note["palate"] or note["finish"]:
                tasting_notes.append(note)
            time.sleep(0.5) # simple rate limit
        except Exception as e:
            print(f"Error fetching detail for {slug}: {e}")
            
    with open(OUTPUT_DIR / "06_sample_detail_raw.jsonl", "w", encoding="utf-8") as f:
        f.write("\n".join(raw_lines) + "\n")
        
    if tasting_notes:
        with open(OUTPUT_DIR / "07_sample_tasting_notes_candidates.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=tasting_notes[0].keys())
            writer.writeheader()
            writer.writerows(tasting_notes)
            
    with open(OUTPUT_DIR / "08_sample_detail_fetch_report.txt", "w", encoding="utf-8") as f:
        f.write(f"Sample details fetched: {len(raw_lines)}\n")
        f.write(f"Tasting notes extracted: {len(tasting_notes)}\n")
    print("Stage 3 complete.")

def stage4_full_api_fetch():
    print("--- Stage 4: Full API Fetch ---")
    all_parsed_items = []
    all_tasting_notes = []
    raw_list_f = open(OUTPUT_DIR / "09_full_review_list_raw.jsonl", "w", encoding="utf-8")
    raw_detail_f = open(OUTPUT_DIR / "11_full_detail_raw.jsonl", "w", encoding="utf-8")
    retry_f = open(OUTPUT_DIR / "14b_retry_later.csv", "w", encoding="utf-8", newline="")
    retry_writer = csv.writer(retry_f)
    retry_writer.writerow(["slug", "error"])
    
    checkpoint_file = OUTPUT_DIR / "13_api_fetch_checkpoint.json"
    processed_slugs = set()
    if checkpoint_file.exists():
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            chk = json.load(f)
            processed_slugs = set(chk.get("processed_slugs", []))
            print(f"Loaded {len(processed_slugs)} processed slugs from checkpoint.")

    page = 1
    per_page = 100
    total_pages = 1
    count = 0
    
    while page <= total_pages:
        try:
            data = fetch_list_page(page, per_page)
            raw_list_f.write(json.dumps(data) + "\n")
            total_pages = (data.get("total", 0) + per_page - 1) // per_page if per_page else 1
            
            items = data.get("items", [])
            for item in items:
                parsed = parse_list_item(item)
                all_parsed_items.append(parsed)
                slug = parsed["slug"]
                if slug in processed_slugs:
                    continue
                
                try:
                    detail = fetch_detail(slug)
                    raw_detail_f.write(json.dumps(detail) + "\n")
                    note = extract_tasting_note(detail)
                    if note["nose"] or note["palate"] or note["finish"]:
                        all_tasting_notes.append(note)
                    processed_slugs.add(slug)
                    count += 1
                    
                    if count % 50 == 0:
                        with open(checkpoint_file, "w", encoding="utf-8") as cf:
                            json.dump({"processed_slugs": list(processed_slugs)}, cf)
                    
                    time.sleep(0.5)
                except Exception as e:
                    print(f"Error detail {slug}: {e}")
                    retry_writer.writerow([slug, str(e)])
                    
            page += 1
            time.sleep(1)
        except Exception as e:
            print(f"Error list page {page}: {e}")
            break

    raw_list_f.close()
    raw_detail_f.close()
    retry_f.close()
    
    if all_parsed_items:
        with open(OUTPUT_DIR / "10_full_review_list_parsed.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_parsed_items[0].keys())
            writer.writeheader()
            writer.writerows(all_parsed_items)
            
    if all_tasting_notes:
        with open(OUTPUT_DIR / "12_full_tasting_notes_candidates.csv", "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_tasting_notes[0].keys())
            writer.writeheader()
            writer.writerows(all_tasting_notes)
            
    with open(OUTPUT_DIR / "14_api_fetch_report.txt", "w", encoding="utf-8") as f:
        f.write(f"Total list items parsed: {len(all_parsed_items)}\n")
        f.write(f"Total details processed: {len(processed_slugs)}\n")
        f.write(f"Total tasting notes extracted: {len(all_tasting_notes)}\n")
    print("Stage 4 complete.")
    return all_parsed_items, all_tasting_notes

def load_master_db(master_path):
    db = []
    with open(master_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            db.append(row)
    return db

def normalize_name(name):
    return clean_text(name).lower()

def match_record(api_record, master_db):
    api_name = normalize_name(api_record.get("name", ""))
    api_age = clean_text(api_record.get("age", ""))
    api_abv = clean_text(api_record.get("abv", ""))
    
    best_match = None
    best_score = 0
    best_category = "rejected"
    
    for row in master_db:
        m_name = normalize_name(row.get("name", ""))
        m_age = clean_text(row.get("age", ""))
        m_abv = clean_text(row.get("abv", ""))
        
        if not m_name:
            continue
            
        # Age or ABV conflict immediately rejects
        if api_age and m_age and api_age != m_age:
            continue
            
        exact = (api_name == m_name)
        score = fuzz.ratio(api_name, m_name) if fuzz else (100 if exact else 0)
        
        if exact and api_age == m_age and api_abv == m_abv and api_abv:
            cat = "high_confidence"
            score = 100
        elif exact and api_age == m_age and not api_abv:
            cat = "manual_review"
            score = 100
        elif score >= 94 and api_age == m_age and api_abv == m_abv:
            cat = "high_confidence"
        elif 88 <= score < 94:
            cat = "manual_review"
        else:
            cat = "rejected"
            
        if score > best_score:
            best_score = score
            best_match = row
            best_category = cat
            
        if cat == "high_confidence":
            break # found best
            
    return best_category, best_match

def stage5_master_match(api_records, master_path):
    print("--- Stage 5: Master Match ---")
    master_db = load_master_db(master_path)
    
    candidates = []
    high_conf = []
    manual = []
    rejected = []
    
    for rec in api_records:
        cat, match = match_record(rec, master_db)
        res = {
            "api_id": rec.get("id"),
            "api_slug": rec.get("slug"),
            "api_name": rec.get("name"),
            "match_category": cat,
            "master_id": match.get("id") if match else "",
            "master_name": match.get("name") if match else ""
        }
        candidates.append(res)
        if cat == "high_confidence":
            high_conf.append(res)
        elif cat == "manual_review":
            manual.append(res)
        else:
            rejected.append(res)
            
    def write_csv(filename, data):
        if not data: return
        with open(OUTPUT_DIR / filename, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            
    write_csv("15_master_match_candidates.csv", candidates)
    write_csv("16_high_confidence_matches.csv", high_conf)
    write_csv("17_manual_review_matches.csv", manual)
    write_csv("18_rejected_matches.csv", rejected)
    
    print(f"Stage 5 complete. High: {len(high_conf)}, Manual: {len(manual)}, Rejected: {len(rejected)}")
    return candidates

def stage6_patch_preview(api_records, tasting_notes, matches):
    print("--- Stage 6: Patch Preview ---")
    patch_notes = []
    rating_meta = []
    price_meta = []
    new_prods = []
    
    match_dict = {m["api_id"]: m for m in matches}
    
    for note in tasting_notes:
        api_id = note.get("source_review_id")
        m = match_dict.get(api_id)
        if m and m["match_category"] == "high_confidence":
            patch_notes.append({
                "master_id": m["master_id"],
                "nose": note["nose"],
                "palate": note["palate"],
                "finish": note["finish"],
                "conclusion_marcel": note["conclusion_marcel"],
                "conclusion_sascha": note["conclusion_sascha"]
            })
            
    for rec in api_records:
        api_id = rec.get("id")
        m = match_dict.get(api_id)
        if m and m["match_category"] == "high_confidence":
            rating_meta.append({
                "master_id": m["master_id"],
                "rating_marcel": rec.get("rating_marcel"),
                "rating_sascha": rec.get("rating_sascha"),
                "rating_value_for_money": rec.get("rating_value_for_money")
            })
            price_meta.append({
                "master_id": m["master_id"],
                "price_per_liter": rec.get("price_per_liter")
            })
        elif m and m["match_category"] == "rejected":
            new_prods.append({
                "api_id": api_id,
                "name": rec.get("name"),
                "age": rec.get("age"),
                "abv": rec.get("abv")
            })
            
    def write_csv(filename, data):
        if not data: return
        with open(OUTPUT_DIR / filename, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
            
    write_csv("19_tasting_notes_patch_preview.csv", patch_notes)
    write_csv("20_rating_metadata_preview.csv", rating_meta)
    write_csv("21_price_metadata_preview.csv", price_meta)
    write_csv("22_new_product_candidates.csv", new_prods)
    
    with open(OUTPUT_DIR / "23_final_report.txt", "w", encoding="utf-8") as f:
        f.write("API extraction completed\n")
        f.write("Master matching completed successfully\n")
        f.write(f"Total API reviews: {len(api_records)}\n")
        f.write(f"Tasting note candidates: {len(tasting_notes)}\n")
        f.write(f"High-confidence master matches: {len(patch_notes)}\n")
        f.write(f"Manual review matches: {len([m for m in matches if m['match_category'] == 'manual_review'])}\n")
        f.write(f"Rejected matches: {len([m for m in matches if m['match_category'] == 'rejected'])}\n")
        f.write(f"New product candidates: {len(new_prods)}\n")
        f.write("Note: rating/price fields are excluded from core import. Patch requires manual approval.\n")
        f.write("Production patch suggestion: Review high-confidence candidates and apply carefully.\n")
    print("Stage 6 complete.")

def run():
    print("Starting Whisky Edition API Source Run...")
    openapi_path = resolve_openapi_path()
    master_path = resolve_master_path()
    
    stage1_openapi_profile(openapi_path)
    sample_items = stage2_sample_fetch()
    if sample_items:
        stage3_sample_detail_fetch(sample_items)
        api_records, tasting_notes = stage4_full_api_fetch()
        
        if master_path:
            matches = stage5_master_match(api_records, master_path)
            stage6_patch_preview(api_records, tasting_notes, matches)
        else:
            print("Master file not found. Skipping Stage 5 and 6.")
            with open(OUTPUT_DIR / "24_master_missing_report.txt", "w", encoding="utf-8") as f:
                f.write("Master missing report\n")
                f.write(f"Searched master path: {FINAL_DIR / '60_FINAL_import_ready_whiskies_distillery_patched.csv'}\n")
                f.write(f"Searched manifest path: {FINAL_DIR / '65_FINAL_IMPORT_FILE_MANIFEST.csv'}\n")
                f.write("Manifest found: No\n")
                f.write("Skipped stages: Stage 5 and Stage 6\n")
                f.write("Required to rerun: Ensure final master CSV is at output/final/60_FINAL_import_ready_whiskies_distillery_patched.csv or specified in manifest.\n")
                
            with open(OUTPUT_DIR / "23_final_report.txt", "w", encoding="utf-8") as f:
                f.write("API extraction completed\n")
                f.write("Master matching skipped\n")
                f.write("Reason: final master file not found\n")
                f.write("Patch preview not generated\n")
                f.write("No master files changed\n")
                if openapi_path:
                    f.write(f"OpenAPI path used: {openapi_path}\n")

if __name__ == "__main__":
    run()
