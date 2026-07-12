import os
import sqlite3
import csv
import json
import re
import difflib
from datetime import datetime
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

def extract_age(name):
    # Check "12 years old", "18yo", "15 year", etc.
    name_lower = name.lower()
    m = re.search(r'\b(\d{1,2})\s*(?:years|year|yo|y\.o\.|y|old)\b', name_lower)
    if m:
        return float(m.group(1))
    m = re.search(r'\b(\d{1,2})\s*-\s*year\s*-old\b', name_lower)
    if m:
        return float(m.group(1))
    # Look for naked numbers that are common ages
    for val in ["25", "18", "15", "12", "10", "8", "30", "21"]:
        if re.search(r'\b' + val + r'\b', name_lower):
            return float(val)
    return None

def extract_abv(name):
    name_lower = name.lower()
    m = re.search(r'\b(\d{2}(?:\.\d+)?)\s*(?:%|vol|strength)\b', name_lower)
    if m:
        return float(m.group(1))
    return None

def extract_vintage(name):
    m = re.search(r'\b(19\d{2}|20[0-2]\d)\b', name)
    if m:
        return int(m.group(1))
    return None

def parse_dist_brand(dbo):
    if not dbo or dbo == "—":
        return "", ""
    parts = [p.strip() for p in dbo.split("-")]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return dbo, dbo

def detect_batch_keywords(name):
    keywords = ["batch", "release", "edition", "cask strength", "ltd", "limited", "single cask", "bottled", "distilled"]
    name_lower = name.lower()
    found = [k for k in keywords if k in name_lower]
    return found

def main():
    print("Reading database...")
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Load distilleries
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
        
    # Load whiskies
    existing_whiskies = {} # whisky_id -> details
    cursor.execute("SELECT whisky_id, name, brand, abv, age_statement, type, distillery_id FROM whiskies;")
    for row in cursor.fetchall():
        w_id = row[0]
        existing_whiskies[w_id] = {
            "name": row[1].strip() if row[1] else "",
            "brand": row[2].strip() if row[2] else "",
            "abv": row[3],
            "age": row[4] if row[4] else "",
            "category": row[5] if row[5] else "",
            "distillery_id": row[6]
        }
        
    # Load unique brands
    existing_brands = set()
    cursor.execute("SELECT DISTINCT brand FROM whiskies WHERE brand IS NOT NULL AND brand != '';")
    for row in cursor.fetchall():
        existing_brands.add(row[0].strip().lower())
    cursor.execute("SELECT DISTINCT brand_name FROM brands WHERE brand_name IS NOT NULL AND brand_name != '';")
    for row in cursor.fetchall():
        existing_brands.add(row[0].strip().lower())
        
    conn.close()
    
    # Read staging files
    staging_cat_path = STAGING_DIR / "staging_catalogue.csv"
    staging_dist_path = STAGING_DIR / "staging_distilleries.csv"
    staging_brands_path = STAGING_DIR / "staging_brands.csv"
    
    cat_review_queue_path = STAGING_DIR / "catalogue_review_queue.csv"
    dist_review_queue_path = STAGING_DIR / "distillery_review_queue.csv"
    brand_review_queue_path = STAGING_DIR / "brand_review_queue.csv"
    
    # ---------------- 1. PROCESS CATALOGUE ----------------
    catalogue_audit_results = []
    
    # Build maps of review queue for easy override if needed
    cat_queue_map = {}
    if cat_review_queue_path.exists():
        with open(cat_review_queue_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                cat_queue_map[int(r["source_row"])] = r
                
    if staging_cat_path.exists():
        with open(staging_cat_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                s_row = int(row["source_row"])
                product_name = row["product_name"]
                dbo = row["distillery_brand_owner"]
                volume = row["volume"]
                w_type = row["type"]
                country = row["country"]
                rating = row["rating"]
                source_file = row["source_file"]
                match_status = row["match_status"]
                matched_id = row["matched_id"]
                confidence = float(row["confidence_score"])
                
                # Parse source fields
                dist, brand = parse_dist_brand(dbo)
                age = extract_age(product_name)
                vintage = extract_vintage(product_name)
                abv = extract_abv(product_name)
                category = w_type
                
                # Query DB details
                db_whisky = None
                db_dist_name = ""
                if matched_id != "None" and matched_id in existing_whiskies:
                    db_whisky = existing_whiskies[matched_id]
                    d_id = db_whisky["distillery_id"]
                    if d_id and d_id in existing_distilleries:
                        db_dist_name = existing_distilleries[d_id]["name"]
                
                # Calculate checks
                exact_match = False
                fuzzy_score = 0.0
                duplicate_risk = "Low"
                split_risk = "Low"
                batch_difference = False
                name_difference = False
                metadata_difference = False
                recommended_action = "CREATE_NEW_PRODUCT"
                reason = "New product candidate"
                
                if db_whisky:
                    exact_match = (product_name.lower().strip() == db_whisky["name"].lower().strip())
                    fuzzy_score = round(get_similarity(product_name, db_whisky["name"]), 4)
                    
                    # Naming difference
                    name_difference = not exact_match
                    
                    # Batch difference
                    source_batch = detect_batch_keywords(product_name)
                    db_batch = detect_batch_keywords(db_whisky["name"])
                    if len(source_batch) != len(db_batch) or set(source_batch) != set(db_batch):
                        batch_difference = True
                        
                    # Metadata difference
                    if abv and db_whisky["abv"] and abs(abv - db_whisky["abv"]) > 0.1:
                        metadata_difference = True
                    if age and db_whisky["age"]:
                        try:
                            db_age = float(re.search(r'\d+', str(db_whisky["age"])).group())
                            if age != db_age:
                                metadata_difference = True
                        except:
                            pass
                            
                    # Risks and recommended action
                    if exact_match:
                        duplicate_risk = "Low"
                        split_risk = "Low"
                        recommended_action = "MERGE_METADATA" if (rating != "0" or row.get("image_url")) else "KEEP_EXISTING"
                        reason = "Only rating/image metadata differs" if recommended_action == "MERGE_METADATA" else "Product matches exactly"
                    else:
                        if batch_difference:
                            duplicate_risk = "High"
                            split_risk = "High"
                            recommended_action = "MERGE_METADATA"
                            reason = "Only batch number/release differs"
                        elif metadata_difference:
                            duplicate_risk = "Medium"
                            split_risk = "High"
                            recommended_action = "MANUAL_REVIEW"
                            reason = "Different abv or age statement"
                        else:
                            duplicate_risk = "High"
                            split_risk = "Medium"
                            recommended_action = "KEEP_EXISTING"
                            reason = "Only naming spelling variation"
                            
                    if confidence < 0.8:
                        if confidence < 0.6:
                            recommended_action = "REJECT"
                            reason = "Extremely low confidence match"
                        else:
                            recommended_action = "MANUAL_REVIEW"
                            reason = "Low confidence fuzzy match"
                else:
                    # New product matching check
                    best_match_id = None
                    best_score = 0.0
                    for ex_id, ex in existing_whiskies.items():
                        score = get_similarity(product_name, ex["name"])
                        if score > best_score:
                            best_score = score
                            best_match_id = ex_id
                            
                    if best_score >= 0.60:
                        ex = existing_whiskies[best_match_id]
                        source_batch = detect_batch_keywords(product_name)
                        if len(source_batch) > 0:
                            duplicate_risk = "High"
                            split_risk = "High"
                            recommended_action = "MERGE_METADATA"
                            reason = f"Batch candidate of existing: {ex['name']}"
                        else:
                            duplicate_risk = "Medium"
                            split_risk = "Medium"
                            recommended_action = "MANUAL_REVIEW"
                            reason = f"Naming candidate of existing: {ex['name']}"
                    else:
                        duplicate_risk = "Low"
                        split_risk = "Low"
                        recommended_action = "CREATE_NEW_PRODUCT"
                        reason = "No similar existing products found"
                        
                # Build audit result row
                catalogue_audit_results.append({
                    "source_row": s_row,
                    "product_name": product_name,
                    "brand": brand,
                    "distillery": dist,
                    "age": age if age else "None",
                    "vintage": vintage if vintage else "None",
                    "abv": abv if abv else "None",
                    "category": category,
                    "source_file": source_file,
                    
                    "whisky_id": matched_id if matched_id != "None" else "None",
                    "db_name": db_whisky["name"] if db_whisky else "None",
                    "db_distillery": db_dist_name if db_dist_name else "None",
                    "db_brand": db_whisky["brand"] if db_whisky else "None",
                    "db_age": db_whisky["age"] if db_whisky else "None",
                    "db_abv": db_whisky["abv"] if db_whisky else "None",
                    "db_category": db_whisky["category"] if db_whisky else "None",
                    
                    "exact_match": "Yes" if exact_match else "No",
                    "fuzzy_score": fuzzy_score,
                    "duplicate_risk": duplicate_risk,
                    "split_risk": split_risk,
                    "batch_difference": "Yes" if batch_difference else "No",
                    "name_difference": "Yes" if name_difference else "No",
                    "metadata_difference": "Yes" if metadata_difference else "No",
                    "recommended_action": recommended_action,
                    "reason": reason,
                    "confidence": confidence
                })
    else:
        print("Warning: staging_catalogue.csv not found.")
        
    # ---------------- 2. PROCESS DISTILLERIES ----------------
    dist_audit_results = []
    
    if staging_dist_path.exists():
        with open(staging_dist_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row["distillery_name"]
                match_status = row["match_status"]
                matched_id = row["matched_id"]
                country = row["country"]
                region = row["region"]
                location = row["location"]
                owner = row["owner"]
                confidence = float(row["confidence_score"])
                s_row = int(row["source_row"])
                
                candidate_name = "None"
                distance_score = 0.0
                name_similarity = 0.0
                recommendation = "CREATE_NEW_DISTILLERY"
                
                if matched_id != "None" and matched_id in existing_distilleries:
                    ex = existing_distilleries[matched_id]
                    candidate_name = ex["name"]
                    name_similarity = round(get_similarity(name, ex["name"]), 4)
                    distance_score = round(1.0 - name_similarity, 4)
                    
                    if match_status == "EXACT_MATCH":
                        recommendation = "MERGE_METADATA"
                    elif match_status == "FUZZY_MATCH":
                        recommendation = "MERGE_METADATA" if name_similarity >= 0.90 else "MANUAL_REVIEW"
                else:
                    # Look for best fuzzy candidate for NEW
                    best_match_id = None
                    best_score = 0.0
                    for ex_id, ex in existing_distilleries.items():
                        score = get_similarity(name, ex["name"])
                        if score > best_score:
                            best_score = score
                            best_match_id = ex_id
                            
                    if best_score >= 0.70:
                        ex = existing_distilleries[best_match_id]
                        candidate_name = ex["name"]
                        name_similarity = round(best_score, 4)
                        distance_score = round(1.0 - best_score, 4)
                        recommendation = "MANUAL_REVIEW"
                        
                dist_audit_results.append({
                    "source_name": name,
                    "candidate_name": candidate_name,
                    "country": country,
                    "region": region,
                    "location": location,
                    "owner": owner,
                    "distance_score": distance_score,
                    "name_similarity": name_similarity,
                    "recommendation": recommendation,
                    "source_row": s_row
                })
    else:
        print("Warning: staging_distilleries.csv not found.")
        
    # ---------------- 3. PROCESS BRANDS ----------------
    brand_audit_results = []
    
    if staging_brands_path.exists():
        with open(staging_brands_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row["brand_name"]
                match_status = row["match_status"]
                matched_id = row["matched_id"]
                owner = row["owner"]
                country = row["country"]
                distillery = row["distillery"]
                confidence = float(row["confidence_score"])
                s_row = int(row["source_row"])
                
                candidate_brand = "None"
                brand_similarity = 0.0
                recommendation = "CREATE_NEW_BRAND"
                
                if matched_id != "None":
                    candidate_brand = matched_id
                    brand_similarity = round(get_similarity(name, matched_id), 4)
                    if match_status == "EXACT_MATCH":
                        recommendation = "MERGE_METADATA"
                    elif match_status == "FUZZY_MATCH":
                        recommendation = "MERGE_METADATA" if brand_similarity >= 0.90 else "MANUAL_REVIEW"
                else:
                    # Look for best fuzzy candidate for NEW
                    best_match = None
                    best_score = 0.0
                    for ex in existing_brands:
                        score = get_similarity(name, ex)
                        if score > best_score:
                            best_score = score
                            best_match = ex
                            
                    if best_score >= 0.70:
                        candidate_brand = best_match
                        brand_similarity = round(best_score, 4)
                        recommendation = "MANUAL_REVIEW"
                        
                brand_audit_results.append({
                    "source_brand": name,
                    "candidate_brand": candidate_brand,
                    "owner": owner,
                    "country": country,
                    "distillery": distillery,
                    "brand_similarity": brand_similarity,
                    "recommendation": recommendation,
                    "source_row": s_row
                })
    else:
        print("Warning: staging_brands.csv not found.")

    # ---------------- WRITE REVIEW DECISIONS TEMPLATE ----------------
    print("Writing review_decisions_template.csv...")
    template_file = STAGING_DIR / "review_decisions_template.csv"
    
    template_rows = []
    
    # Process Catalogue
    for item in catalogue_audit_results:
        template_rows.append({
            "decision": "",
            "reviewer": "",
            "review_date": "",
            "entity_type": "whisky",
            "source_file": item["source_file"],
            "source_row": item["source_row"],
            "candidate_id": item["whisky_id"],
            "candidate_name": item["db_name"],
            "recommended_action": item["recommended_action"],
            "reviewer_action": "",
            "notes": f"Reason: {item['reason']}. Duplicate Risk: {item['duplicate_risk']}. Split Risk: {item['split_risk']}"
        })
        
    # Process Distilleries
    for item in dist_audit_results:
        template_rows.append({
            "decision": "",
            "reviewer": "",
            "review_date": "",
            "entity_type": "distillery",
            "source_file": "distilleries.csv",
            "source_row": item["source_row"],
            "candidate_id": "N/A",
            "candidate_name": item["candidate_name"],
            "recommended_action": item["recommendation"],
            "reviewer_action": "",
            "notes": f"Distillery name: {item['source_name']}. Similarity: {item['name_similarity']}"
        })
        
    # Process Brands
    for item in brand_audit_results:
        template_rows.append({
            "decision": "",
            "reviewer": "",
            "review_date": "",
            "entity_type": "brand",
            "source_file": "brands.csv",
            "source_row": item["source_row"],
            "candidate_id": "N/A",
            "candidate_name": item["candidate_brand"],
            "recommended_action": item["recommendation"],
            "reviewer_action": "",
            "notes": f"Brand name: {item['source_brand']}. Similarity: {item['brand_similarity']}"
        })
        
    with open(template_file, "w", newline="", encoding="utf-8") as f:
        if template_rows:
            writer = csv.DictWriter(f, fieldnames=template_rows[0].keys())
            writer.writeheader()
            writer.writerows(template_rows)
    print(f"Saved template file: {template_file}")
    
    # ---------------- GENERATE MANUAL REVIEW DASHBOARD ----------------
    print("Generating manual_review_dashboard.md...")
    
    # Statistics
    total_records = len(template_rows)
    keep_existing = sum(1 for r in catalogue_audit_results if r["recommended_action"] == "KEEP_EXISTING")
    merge_metadata = (
        sum(1 for r in catalogue_audit_results if r["recommended_action"] == "MERGE_METADATA") +
        sum(1 for r in dist_audit_results if r["recommendation"] == "MERGE_METADATA") +
        sum(1 for r in brand_audit_results if r["recommendation"] == "MERGE_METADATA")
    )
    create_new_product = sum(1 for r in catalogue_audit_results if r["recommended_action"] == "CREATE_NEW_PRODUCT")
    create_new_brand = sum(1 for r in brand_audit_results if r["recommendation"] == "CREATE_NEW_BRAND")
    create_new_dist = sum(1 for r in dist_audit_results if r["recommendation"] == "CREATE_NEW_DISTILLERY")
    manual_review = (
        sum(1 for r in catalogue_audit_results if r["recommended_action"] == "MANUAL_REVIEW") +
        sum(1 for r in dist_audit_results if r["recommendation"] == "MANUAL_REVIEW") +
        sum(1 for r in brand_audit_results if r["recommendation"] == "MANUAL_REVIEW")
    )
    reject = sum(1 for r in catalogue_audit_results if r["recommended_action"] == "REJECT")
    
    # Get top 100 most risky catalogue items
    def cat_risk_score(item):
        d_risk = item["duplicate_risk"].lower()
        s_risk = item["split_risk"].lower()
        score = 0
        if "high" in d_risk: score += 10
        elif "medium" in d_risk: score += 5
        if "high" in s_risk: score += 10
        elif "medium" in s_risk: score += 5
        conf = float(item["confidence"])
        return (score, -conf)
        
    sorted_cat_risks = sorted(catalogue_audit_results, key=cat_risk_score, reverse=True)
    top_100_risky = sorted_cat_risks[:100]
    
    # High confidence new products
    new_products = [r for r in catalogue_audit_results if r["recommended_action"] == "CREATE_NEW_PRODUCT"]
    high_conf_new_products = sorted(new_products, key=lambda x: x["confidence"], reverse=True)[:20]
    
    # High confidence merge candidates
    merge_products = [r for r in catalogue_audit_results if r["recommended_action"] == "MERGE_METADATA"]
    high_conf_merge_products = sorted(merge_products, key=lambda x: x["confidence"], reverse=True)[:20]
    
    dashboard_file = REPORT_DIR / "manual_review_dashboard.md"
    with open(dashboard_file, "w", encoding="utf-8") as f:
        f.write("# Malt Radar - Manuel İnceleme Asistanı Paneli (Manual Review Dashboard)\n\n")
        f.write("**Oluşturulma Tarihi:** 2026-07-12\n")
        f.write("**Kaynak Dizin:** `output/import/books/`\n")
        f.write("**Yüklenen Veritabanı:** `output/import/production.db` (Salt Okunur)\n\n")
        
        f.write("## 1. Genel Dağılım Metrikleri\n")
        f.write(f"- **Toplam İnceleme Adayı Kayıt (Katalog + Üretici + Marka):** {total_records}\n")
        f.write(f"  - `KEEP_EXISTING` (Mevcut viskiyi aynen koru): {keep_existing}\n")
        f.write(f"  - `MERGE_METADATA` (Metadata / değer güncelle): {merge_metadata}\n")
        f.write(f"  - `CREATE_NEW_PRODUCT` (Yeni viski oluştur): {create_new_product}\n")
        f.write(f"  - `CREATE_NEW_BRAND` (Yeni marka oluştur): {create_new_brand}\n")
        f.write(f"  - `CREATE_NEW_DISTILLERY` (Yeni damıtımevi oluştur): {create_new_dist}\n")
        f.write(f"  - `MANUAL_REVIEW` (Detaylı manuel inceleme gerektiren): {manual_review}\n")
        f.write(f"  - `REJECT` (Düşük güvenli reddedilen kayıtlar): {reject}\n\n")
        
        f.write("## 2. En Riskli 100 Katalog Kaydı (Mükerrer ve Bölünme Tehdidi)\n")
        f.write("Aşağıdaki kayıtlar, mevcuttaki viskilerle çakışan batch/release yapısı veya yazım farklılıkları nedeniyle **yüksek bölünme (split)** veya **mükerrer kart (duplicate)** riski içermektedir:\n\n")
        f.write("| Satır | Ürün Adı | Mevcut Eşleşme Adayı | Önerilen Aksiyon | Çakışma Nedeni / Gerekçe | Güven |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")
        for item in top_100_risky:
            f.write(f"| {item['source_row']} | {item['product_name']} | `{item['whisky_id']}` ({item['db_name']}) | **{item['recommended_action']}** | {item['reason']} | {item['confidence']} |\n")
            
        f.write("\n## 3. En Yüksek Güven Skorlu Yeni Ürün Adayları (Top 20)\n")
        f.write("Veritabanında hiçbir benzer kaydı bulunmayan ve yeni eklenmesi önerilen en yüksek güven puanlı adaylar:\n\n")
        f.write("| Satır | Ürün Adı | Marka | Damıtımevi | Kategori | Güven Skoru |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")
        for item in high_conf_new_products:
            f.write(f"| {item['source_row']} | {item['product_name']} | {item['brand']} | {item['distillery']} | {item['category']} | {item['confidence']} |\n")
            
        f.write("\n## 4. En Yüksek Güven Skorlu Birleştirme (Merge) Adayları (Top 20)\n")
        f.write("Mevcut viski kayıtlarıyla birebir veya çok yüksek oranda eşleşen, metadata zenginleştirmeye (rating/görsel) uygun kayıtlar:\n\n")
        f.write("| Satır | Ürün Adı | Mevcut Eşleşme | Güven | Neden / Gerekçe |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        for item in high_conf_merge_products:
            f.write(f"| {item['source_row']} | {item['product_name']} | `{item['whisky_id']}` ({item['db_name']}) | {item['confidence']} | {item['reason']} |\n")
            
        f.write("\n## 5. Uygulanan Malt Radar Kalite Güvence Kuralları\n")
        f.write("- **Batch Farkları:** Aynı ürünün farklı batch'leri (örneğin *Highland Park Cask Strength Release No. 1, 2, 3, 4, 5*) için ayrı viski kartı açılmaz. Bu kayıtlar mevcut ana viski kartı altında `MERGE_METADATA` eylemi ile toplanmalı ve batch bilgisi metadata olarak kalmalıdır.\n")
        f.write("- **Tadım Profili Kısıtlaması:** Batch'ler arasında duyusal bir fark kanıtlanmadığı sürece her yeni batch için ek tadım profili açılması kesinlikle engellenmiştir.\n")
        f.write("- **İzlenebilirlik ve Güvenlik:** Kaynak kitap bilgileri veritabanında sadece dahili metadata olarak tutulacaktır.\n")

    print(f"Manual review dashboard written to {dashboard_file}")

if __name__ == "__main__":
    main()
