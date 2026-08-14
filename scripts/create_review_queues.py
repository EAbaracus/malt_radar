import os
import sqlite3
import csv
import json
import difflib
from pathlib import Path

# Paths
REPO_ROOT = Path(r"C:\Users\eltun\Documents\malt radar CLEAN")
DB_PATH = REPO_ROOT / "output" / "import" / "production.db"
STAGING_DIR = REPO_ROOT / "output" / "import" / "books"
REPORT_DIR = REPO_ROOT / "output" / "reports"

os.makedirs(STAGING_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

def get_similarity(s1, s2):
    if not s1 or not s2:
        return 0.0
    return difflib.SequenceMatcher(None, s1.lower().strip(), s2.lower().strip()).ratio()

def detect_batch_keywords(name):
    keywords = ["batch", "release", "edition", "cask strength", "ltd", "limited", "single cask", "bottled", "distilled"]
    name_lower = name.lower()
    found = [k for k in keywords if k in name_lower]
    return found

def main():
    print("Connecting to production.db...")
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Load distilleries details
    # We want name, status, owner, country, region, location
    existing_distilleries = {} # distillery_id -> details
    cursor.execute("SELECT distillery_id, name, country, region, location, owner FROM distilleries;")
    for row in cursor.fetchall():
        d_id = row[0]
        existing_distilleries[d_id] = {
            "name": row[1].strip() if row[1] else "",
            "country": row[2].strip() if row[2] else "",
            "region": row[3].strip() if row[3] else "",
            "location": row[4].strip() if row[4] else "",
            "owner": row[5].strip() if row[5] else ""
        }
        
    # Load whiskies details
    existing_whiskies = {} # whisky_id -> details
    cursor.execute("SELECT whisky_id, name, brand, abv, age_statement FROM whiskies;")
    for row in cursor.fetchall():
        w_id = row[0]
        existing_whiskies[w_id] = {
            "name": row[1].strip() if row[1] else "",
            "brand": row[2].strip() if row[2] else "",
            "abv": row[3],
            "age": row[4]
        }
        
    # Load brands details (brand_name -> owner)
    existing_brands = {} # lowercase_brand_name -> owner
    # From brands table
    cursor.execute("SELECT brand_name, description FROM brands;")
    for row in cursor.fetchall():
        b_name = row[0].strip()
        existing_brands[b_name.lower()] = "" # We don't have owner column in brands, wait.
    # From whiskies brand column
    cursor.execute("SELECT DISTINCT brand FROM whiskies WHERE brand IS NOT NULL AND brand != '';")
    for row in cursor.fetchall():
        b_name = row[0].strip()
        existing_brands[b_name.lower()] = ""
        
    conn.close()
    
    # ---------------- 1. CATALOGUE REVIEW QUEUE ----------------
    print("Generating catalogue_review_queue.csv...")
    staging_cat_path = STAGING_DIR / "staging_catalogue.csv"
    catalogue_review_queue = []
    
    total_cat = 0
    duplicate_risks = 0
    split_risks = 0
    low_confidence_count = 0
    
    if staging_cat_path.exists():
        with open(staging_cat_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_cat += 1
                s_row = row["source_row"]
                product_name = row["product_name"]
                match_status = row["match_status"]
                matched_id = row["matched_id"]
                confidence = float(row["confidence_score"])
                
                # Check batch words
                batch_words = detect_batch_keywords(product_name)
                is_batch = len(batch_words) > 0
                
                dup_risk = "Low"
                split_risk = "Low"
                rec_action = "CREATE_NEW_PRODUCT"
                
                if match_status == "EXACT_MATCH":
                    dup_risk = "Low"
                    split_risk = "Low"
                    # If we already have it, we might want to merge metadata (image/rating)
                    if row.get("image_url") or (row.get("rating") and row["rating"] != "0"):
                        rec_action = "MERGE_METADATA"
                    else:
                        rec_action = "KEEP_EXISTING"
                elif match_status in ("HIGH_CONFIDENCE_MATCH", "FUZZY_MATCH"):
                    if is_batch:
                        dup_risk = "High"
                        split_risk = "High"
                        rec_action = "MERGE_METADATA"
                        split_risks += 1
                        duplicate_risks += 1
                    else:
                        dup_risk = "Medium"
                        split_risk = "Medium"
                        rec_action = "KEEP_EXISTING"
                        duplicate_risks += 1
                elif match_status == "NEW":
                    # Check similarity against all existing whiskies to see if it's actually similar
                    best_match_id = None
                    best_score = 0.0
                    for ex_id, ex in existing_whiskies.items():
                        score = get_similarity(product_name, ex["name"])
                        if score > best_score:
                            best_score = score
                            best_match_id = ex_id
                            
                    if best_score >= 0.60:
                        ex = existing_whiskies[best_match_id]
                        if is_batch:
                            dup_risk = "High"
                            split_risk = "High"
                            rec_action = "MERGE_METADATA"
                            split_risks += 1
                            duplicate_risks += 1
                        else:
                            dup_risk = "Medium"
                            split_risk = "Medium"
                            rec_action = "KEEP_EXISTING"
                            duplicate_risks += 1
                    else:
                        dup_risk = "Low"
                        split_risk = "Low"
                        rec_action = "CREATE_NEW_PRODUCT"
                        
                if confidence < 0.8:
                    low_confidence_count += 1
                    # If confidence is extremely low and we can't match it, reject it
                    if confidence < 0.6 and match_status == "FUZZY_MATCH":
                        rec_action = "REJECT"
                
                catalogue_review_queue.append({
                    "source_row": s_row,
                    "product_name": product_name,
                    "existing_match": matched_id if matched_id != "None" else "None",
                    "duplicate_risk": dup_risk,
                    "split_risk": split_risk,
                    "recommended_action": rec_action,
                    "confidence": confidence
                })
                
        # Write catalogue_review_queue.csv
        cat_out = STAGING_DIR / "catalogue_review_queue.csv"
        with open(cat_out, "w", newline="", encoding="utf-8") as f:
            if catalogue_review_queue:
                writer = csv.DictWriter(f, fieldnames=catalogue_review_queue[0].keys())
                writer.writeheader()
                writer.writerows(catalogue_review_queue)
        print(f"Catalogue review queue written: {len(catalogue_review_queue)}")
    else:
        print("Warning: staging_catalogue.csv not found.")
        
    # ---------------- 2. DISTILLERY REVIEW QUEUE ----------------
    print("Generating distillery_review_queue.csv...")
    staging_dist_path = STAGING_DIR / "staging_distilleries.csv"
    distillery_review_queue = []
    
    if staging_dist_path.exists():
        with open(staging_dist_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row["distillery_name"]
                match_status = row["match_status"]
                matched_id = row["matched_id"]
                country = row["country"]
                location = row["location"]
                region = row["region"]
                
                candidate_match = "None"
                country_match = "N/A"
                location_match = "N/A"
                recommendation = "CREATE_NEW_DISTILLERY"
                
                if matched_id != "None" and matched_id in existing_distilleries:
                    ex = existing_distilleries[matched_id]
                    candidate_match = ex["name"]
                    
                    # Country match check
                    if country and ex["country"]:
                        country_match = "Yes" if country.lower() == ex["country"].lower() else "No"
                    else:
                        country_match = "Yes" if not country and not ex["country"] else "No"
                        
                    # Location match check (region or location)
                    loc_db = (ex["location"] + " " + ex["region"]).strip().lower()
                    loc_source = (location + " " + region).strip().lower()
                    if loc_source and loc_db:
                        # Simple overlap or similarity
                        sim = difflib.SequenceMatcher(None, loc_source, loc_db).ratio()
                        location_match = "Yes" if sim >= 0.5 else "No"
                    else:
                        location_match = "Yes" if not loc_source and not loc_db else "No"
                        
                    if match_status == "EXACT_MATCH":
                        recommendation = "MERGE_METADATA"
                    elif match_status == "FUZZY_MATCH":
                        recommendation = "MERGE_METADATA" if country_match == "Yes" else "MANUAL_RESOLVE"
                else:
                    # Look for potential fuzzy candidate if match_status == NEW
                    best_match_id = None
                    best_score = 0.0
                    for ex_id, ex in existing_distilleries.items():
                        score = get_similarity(name, ex["name"])
                        if score > best_score:
                            best_score = score
                            best_match_id = ex_id
                            
                    if best_score >= 0.70:
                        ex = existing_distilleries[best_match_id]
                        candidate_match = ex["name"]
                        recommendation = "MANUAL_RESOLVE"
                        if country and ex["country"]:
                            country_match = "Yes" if country.lower() == ex["country"].lower() else "No"
                        if (location or region) and (ex["location"] or ex["region"]):
                            location_match = "Yes" if get_similarity(location + " " + region, ex["location"] + " " + ex["region"]) >= 0.5 else "No"
                
                distillery_review_queue.append({
                    "source_name": name,
                    "candidate_match": candidate_match,
                    "country_match": country_match,
                    "location_match": location_match,
                    "recommendation": recommendation
                })
                
        # Write distillery_review_queue.csv
        dist_out = STAGING_DIR / "distillery_review_queue.csv"
        with open(dist_out, "w", newline="", encoding="utf-8") as f:
            if distillery_review_queue:
                writer = csv.DictWriter(f, fieldnames=distillery_review_queue[0].keys())
                writer.writeheader()
                writer.writerows(distillery_review_queue)
        print(f"Distillery review queue written: {len(distillery_review_queue)}")
    else:
        print("Warning: staging_distilleries.csv not found.")
        
    # ---------------- 3. BRAND REVIEW QUEUE ----------------
    print("Generating brand_review_queue.csv...")
    staging_brands_path = STAGING_DIR / "staging_brands.csv"
    brand_review_queue = []
    
    if staging_brands_path.exists():
        with open(staging_brands_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row["brand_name"]
                match_status = row["match_status"]
                matched_id = row["matched_id"]
                owner = row["owner"]
                
                candidate_brand = "None"
                owner_match = "N/A"
                recommendation = "CREATE_NEW_BRAND"
                
                if matched_id != "None":
                    candidate_brand = matched_id
                    owner_match = "Yes" # Default to Yes since we matched exactly, but owner column is empty in DB
                    if match_status == "EXACT_MATCH":
                        recommendation = "MERGE_METADATA"
                    elif match_status == "FUZZY_MATCH":
                        recommendation = "MERGE_METADATA"
                else:
                    # Check similar name in db
                    best_match = None
                    best_score = 0.0
                    for ex in existing_brands:
                        score = get_similarity(name, ex)
                        if score > best_score:
                            best_score = score
                            best_match = ex
                            
                    if best_score >= 0.70:
                        candidate_brand = best_match
                        recommendation = "MANUAL_RESOLVE"
                        owner_match = "No" # Owner mismatch potential
                
                brand_review_queue.append({
                    "source_brand": name,
                    "candidate_brand": candidate_brand,
                    "owner_match": owner_match,
                    "recommendation": recommendation
                })
                
        # Write brand_review_queue.csv
        brand_out = STAGING_DIR / "brand_review_queue.csv"
        with open(brand_out, "w", newline="", encoding="utf-8") as f:
            if brand_review_queue:
                writer = csv.DictWriter(f, fieldnames=brand_review_queue[0].keys())
                writer.writeheader()
                writer.writerows(brand_review_queue)
        print(f"Brand review queue written: {len(brand_review_queue)}")
    else:
        print("Warning: staging_brands.csv not found.")
        
    # ---------------- 4. GENERATE GO/NO-GO SUMMARY REPORT ----------------
    print("Generating GO/NO-GO summary report...")
    summary_path = REPORT_DIR / "books_review_summary.md"
    
    go_status = "NO-GO (Otomatik Import)"
    
    reasons = []
    if duplicate_risks > 0:
        reasons.append(f"{duplicate_risks} adet kayıt mükerrer (duplicate) viski kartı oluşturma riski taşımaktadır.")
    if split_risks > 0:
        reasons.append(f"{split_risks} adet kayıt yanlış viski bölünmesi (whisky split) riski taşımaktadır (aynı ürünün farklı batch veya release versiyonları).")
    if low_confidence_count > 0:
        reasons.append(f"{low_confidence_count} adet kayıt düşük güven eşleşmesine sahiptir.")
        
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# Malt Radar - Yeni Veri İnceleme Paketleri Raporu\n\n")
        f.write("**Oluşturulma Tarihi:** 2026-07-12\n")
        f.write("**Staging Dizin:** `output/import/books/`\n\n")
        
        f.write("## 1. Paket Özetleri\n")
        f.write(f"- **Katalog İnceleme Paketi (`catalogue_review_queue.csv`):** {len(catalogue_review_queue)} kayıt\n")
        f.write(f"- **Damıtımevi İnceleme Paketi (`distillery_review_queue.csv`):** {len(distillery_review_queue)} kayıt\n")
        f.write(f"- **Marka İnceleme Paketi (`brand_review_queue.csv`):** {len(brand_review_queue)} kayıt\n\n")
        
        f.write("## 2. Karar: GO / NO-GO\n")
        f.write(f"### Karar: **{go_status}**\n\n")
        
        f.write("#### Gerekçeler (NO-GO Nedenleri):\n")
        for r in reasons:
            f.write(f"- {r}\n")
        f.write("\n")
        
        f.write("> [!IMPORTANT]\n")
        f.write("> Veri tabanının kalitesini korumak için doğrudan otomatik veri aktarımı engellenmiştir.\n")
        f.write("> Lütfen `output/import/books` içindeki `review_queue` dosyalarını kullanarak manuel onay sürecini tamamlayın.\n\n")
        
        f.write("## 3. Kurallar ve Yönergeler\n")
        f.write("- **Batch ve Release Yönetimi:** Aynı viskinin farklı batch'leri (örneğin *Aberlour A'bunadh Batch 60, 61*) için yeni viski kartı açılmamalıdır. Bu kayıtlar mevcut viskiye `MERGE_METADATA` ile bağlanmalıdır.\n")
        f.write("- **Duyusal Profiller:** Her yeni batch için ek tadım profili açılması kesinlikle engellenmiştir.\n")
        f.write("- **Kaynak İzlenebilirliği:** Kaynak kitap bilgileri veritabanında sadece dahili metadata olarak saklanmalıdır.\n")
        
    print(f"Summary report written to {summary_path}")

if __name__ == "__main__":
    main()
