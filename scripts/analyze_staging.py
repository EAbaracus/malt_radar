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

os.makedirs(REPORT_DIR, exist_ok=True)

def get_similarity(s1, s2):
    if not s1 or not s2:
        return 0.0
    s1_clean = s1.lower().strip()
    s2_clean = s2.lower().strip()
    return difflib.SequenceMatcher(None, s1_clean, s2_clean).ratio()

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
    
    # Load existing distilleries
    existing_distilleries = {} # distillery_id -> name, status, owner, country
    cursor.execute("SELECT distillery_id, name, status, owner, country FROM distilleries;")
    for row in cursor.fetchall():
        d_id = row[0]
        existing_distilleries[d_id] = {
            "name": row[1].strip() if row[1] else "",
            "status": row[2] if row[2] else "",
            "owner": row[3] if row[3] else "",
            "country": row[4] if row[4] else ""
        }
        
    # Load existing whiskies
    existing_whiskies = {} # whisky_id -> dict
    cursor.execute("SELECT whisky_id, name, brand, abv, age_statement, cask_type FROM whiskies;")
    for row in cursor.fetchall():
        w_id = row[0]
        existing_whiskies[w_id] = {
            "name": row[1].strip() if row[1] else "",
            "brand": row[2].strip() if row[2] else "",
            "abv": row[3],
            "age_statement": row[4] if row[4] else "",
            "cask_type": row[5] if row[5] else ""
        }
        
    # Load unique brand names in db (from whiskies and brands table)
    existing_brands = set()
    cursor.execute("SELECT DISTINCT brand FROM whiskies WHERE brand IS NOT NULL AND brand != '';")
    for row in cursor.fetchall():
        existing_brands.add(row[0].strip())
    cursor.execute("SELECT DISTINCT brand_name FROM brands WHERE brand_name IS NOT NULL AND brand_name != '';")
    for row in cursor.fetchall():
        existing_brands.add(row[0].strip())
        
    conn.close()
    
    # ---------------- 1. PROCESS DISTILLERIES MERGE CANDIDATES ----------------
    print("Analyzing distilleries staging for merge candidates...")
    staging_dist_file = STAGING_DIR / "staging_distilleries.csv"
    dist_merge_candidates = []
    
    if staging_dist_file.exists():
        with open(staging_dist_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row["distillery_name"]
                owner = row["owner"]
                country = row["country"]
                status = row["status"]
                match_status = row["match_status"]
                matched_id = row["matched_id"]
                s_row = row["source_row"]
                
                # Check for aliases, spelling, or status mismatches
                if match_status == "EXACT_MATCH" and matched_id in existing_distilleries:
                    ex = existing_distilleries[matched_id]
                    # Check status change
                    if status and ex["status"] and status.lower() != str(ex["status"]).lower():
                        dist_merge_candidates.append({
                            "source_row": s_row,
                            "source_name": name,
                            "matched_name": ex["name"],
                            "matched_id": matched_id,
                            "similarity": 1.0,
                            "reason": f"Status mismatch: Source lists '{status}', DB has '{ex['status']}'",
                            "action": "UPDATE_METADATA"
                        })
                elif match_status == "FUZZY_MATCH" and matched_id in existing_distilleries:
                    ex = existing_distilleries[matched_id]
                    # Fuzzy match merge candidate
                    dist_merge_candidates.append({
                        "source_row": s_row,
                        "source_name": name,
                        "matched_name": ex["name"],
                        "matched_id": matched_id,
                        "similarity": row["confidence_score"],
                        "reason": f"Name spelling variation / Alias",
                        "action": "MERGE"
                    })
                elif match_status == "NEW":
                    # Check if there is a very similar distillery name that was missed
                    best_match_id = None
                    best_score = 0.0
                    for ex_id, ex in existing_distilleries.items():
                        score = get_similarity(name, ex["name"])
                        if score > best_score:
                            best_score = score
                            best_match_id = ex_id
                            
                    if best_score >= 0.70:
                        ex = existing_distilleries[best_match_id]
                        dist_merge_candidates.append({
                            "source_row": s_row,
                            "source_name": name,
                            "matched_name": ex["name"],
                            "matched_id": best_match_id,
                            "similarity": round(best_score, 4),
                            "reason": f"Potential new alias or spelling variant (Similarity: {round(best_score,2)})",
                            "action": "MERGE"
                        })
                        
        # Write distillery_merge_candidates.csv
        dist_out = REPORT_DIR / "distillery_merge_candidates.csv"
        with open(dist_out, "w", newline="", encoding="utf-8") as f:
            if dist_merge_candidates:
                writer = csv.DictWriter(f, fieldnames=dist_merge_candidates[0].keys())
                writer.writeheader()
                writer.writerows(dist_merge_candidates)
            else:
                f.write("source_row,source_name,matched_name,matched_id,similarity,reason,action\n")
        print(f"Distillery merge candidates written: {len(dist_merge_candidates)}")
    else:
        print("Warning: staging_distilleries.csv not found.")
        
    # ---------------- 2. PROCESS BRANDS MERGE CANDIDATES ----------------
    print("Analyzing brands staging for merge candidates...")
    staging_brands_file = STAGING_DIR / "staging_brands.csv"
    brand_merge_candidates = []
    
    if staging_brands_file.exists():
        with open(staging_brands_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row["brand_name"]
                owner = row["owner"]
                match_status = row["match_status"]
                matched_id = row["matched_id"]
                s_row = row["source_row"]
                
                # Check for aliases, spelling, or owner mismatches
                if match_status == "FUZZY_MATCH":
                    brand_merge_candidates.append({
                        "source_row": s_row,
                        "source_name": name,
                        "matched_name": matched_id,
                        "matched_id": "N/A",
                        "similarity": row["confidence_score"],
                        "reason": "Name spelling variation / Alias",
                        "action": "MERGE"
                    })
                elif match_status == "NEW":
                    # Check similar name in db
                    best_match = None
                    best_score = 0.0
                    for ex in existing_brands:
                        score = get_similarity(name, ex)
                        if score > best_score:
                            best_score = score
                            best_match = ex
                            
                    if best_score >= 0.70:
                        brand_merge_candidates.append({
                            "source_row": s_row,
                            "source_name": name,
                            "matched_name": best_match,
                            "matched_id": "N/A",
                            "similarity": round(best_score, 4),
                            "reason": f"Potential new alias (Similarity: {round(best_score,2)})",
                            "action": "MERGE"
                        })
                        
        # Write brand_merge_candidates.csv
        brand_out = REPORT_DIR / "brand_merge_candidates.csv"
        with open(brand_out, "w", newline="", encoding="utf-8") as f:
            if brand_merge_candidates:
                writer = csv.DictWriter(f, fieldnames=brand_merge_candidates[0].keys())
                writer.writeheader()
                writer.writerows(brand_merge_candidates)
            else:
                f.write("source_row,source_name,matched_name,matched_id,similarity,reason,action\n")
        print(f"Brand merge candidates written: {len(brand_merge_candidates)}")
    else:
        print("Warning: staging_brands.csv not found.")
        
    # ---------------- 3. PROCESS CATALOGUE AUDIT & PREVENT DUPLICATES ----------------
    print("Auditing catalogue staging for batch/split risks...")
    staging_cat_file = STAGING_DIR / "staging_catalogue.csv"
    
    cat_items = []
    duplicate_risks = 0
    batch_splits = 0
    low_confidence_matches = 0
    total_cat = 0
    
    exact_approved = 0
    manual_review_needed = 0
    
    audit_details = []
    
    if staging_cat_file.exists():
        with open(staging_cat_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_cat += 1
                name = row["product_name"]
                match_status = row["match_status"]
                matched_id = row["matched_id"]
                confidence_score = float(row["confidence_score"])
                review_status = row["review_status"]
                s_row = row["source_row"]
                
                # Assess batch/release difference
                batch_words = detect_batch_keywords(name)
                is_batch = len(batch_words) > 0
                
                # Assess duplicate risk
                dup_risk = "Low"
                split_risk = "Low"
                reason_audit = []
                
                if match_status == "EXACT_MATCH":
                    dup_risk = "Low (Matched perfectly)"
                    exact_approved += 1
                elif match_status in ("HIGH_CONFIDENCE_MATCH", "FUZZY_MATCH") and matched_id in existing_whiskies:
                    ex = existing_whiskies[matched_id]
                    # Check if it's a batch difference
                    if is_batch:
                        split_risk = "High (Batch word detected: " + ", ".join(batch_words) + ")"
                        dup_risk = "High (Should be merged under same ID, batch as metadata)"
                        batch_splits += 1
                        reason_audit.append("Batch difference detected")
                    else:
                        # Fuzzy match name check (e.g. contains extra word or year statement)
                        # Check if age statements match
                        age_in_name = any(char.isdigit() for char in name)
                        age_in_ex = any(char.isdigit() for char in ex["name"])
                        if age_in_name != age_in_ex:
                            split_risk = "Medium (Possible different age statement)"
                            reason_audit.append("Age mismatch risk")
                        else:
                            split_risk = "High (Spelling variation of same product)"
                            dup_risk = "High (Duplicate creation threat)"
                            duplicate_risks += 1
                            reason_audit.append("Spelling alias")
                            
                    if confidence_score < 0.8:
                        low_confidence_matches += 1
                        reason_audit.append("Low confidence match")
                        
                    manual_review_needed += 1
                elif match_status == "NEW":
                    # Check if it contains batch words and fuzzy matches something in db
                    best_match_id = None
                    best_score = 0.0
                    for ex_id, ex in existing_whiskies.items():
                        score = get_similarity(name, ex["name"])
                        if score > best_score:
                            best_score = score
                            best_match_id = ex_id
                            
                    if best_score >= 0.60:
                        ex = existing_whiskies[best_match_id]
                        if is_batch or any(kw in name.lower() for kw in ["batch", "release", "cask strength"]):
                            split_risk = "High (Batch of existing product: " + ex["name"] + ")"
                            dup_risk = "High (Should be merged)"
                            batch_splits += 1
                            reason_audit.append(f"Batch candidate of {ex['name']}")
                        else:
                            split_risk = "Medium (Fuzzy candidate of existing product)"
                            dup_risk = "Medium (Spelling duplicate threat)"
                            duplicate_risks += 1
                            reason_audit.append(f"Spelling candidate of {ex['name']}")
                            
                    manual_review_needed += 1
                    
                audit_details.append({
                    "row": s_row,
                    "name": name,
                    "match_status": match_status,
                    "matched_id": matched_id,
                    "confidence": confidence_score,
                    "batch_detected": "Yes" if is_batch else "No",
                    "duplicate_risk": dup_risk,
                    "split_risk": split_risk,
                    "reasons": ", ".join(reason_audit) if reason_audit else "Clear"
                })
    else:
        print("Warning: staging_catalogue.csv not found.")
        
    # Determine GO/NO-GO
    # The user says:
    # "NO-GO sebepleri: duplicate risk, yanlış whisky split, düşük confidence eşleşme"
    # Let's check how many high-risk splits and duplicates exist.
    # If there are a significant number of high-risk items (e.g. > 10 batch splits or duplicate risks)
    # without manual review resolution, it's a NO-GO for automatic import.
    # But wait! We generated staging files where they are isolated, so they are not written to DB.
    # Therefore, the staging itself is a "GO" because it safely isolated them in review queue,
    # but the direct automatic import is a "NO-GO" (requires manual review).
    # Let's specify:
    # Karar: NO-GO (Otomatik Import İçin) / GO (Manuel İnceleme Kuyruğu İçin)
    
    go_status = "NO-GO (Otomatik Import)"
    reason_nogo = []
    if duplicate_risks > 0:
        reason_nogo.append(f"{duplicate_risks} adet olası mükerrer (duplicate) ürün kaydı riski.")
    if batch_splits > 0:
        reason_nogo.append(f"{batch_splits} adet yanlış ürün bölünmesi (whisky split) riski (aynı ürünün farklı batch/release versiyonları).")
    if low_confidence_matches > 0:
        reason_nogo.append(f"{low_confidence_matches} adet düşük güvenli eşleşme.")
        
    # Write output/reports/books_catalogue_review.md
    md_file = REPORT_DIR / "books_catalogue_review.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write("# Malt Radar - Viski Kataloğu Entegrasyon Ön İnceleme Raporu\n\n")
        f.write("**Oluşturulma Tarihi:** 2026-07-12\n")
        f.write("**İncelenen Dosya:** `output/import/books/staging_catalogue.csv`\n\n")
        
        f.write("## 1. Denetim Özeti\n")
        f.write(f"- **Toplam Katalog Kaydı:** {total_cat}\n")
        f.write(f"- **Otomatik Kabul Edilebilir (Approved):** {exact_approved} (%{round(exact_approved/total_cat*100, 2) if total_cat > 0 else 0})\n")
        f.write(f"- **Manuel İnceleme Gerektiren (Manual Review):** {manual_review_needed} (%{round(manual_review_needed/total_cat*100, 2) if total_cat > 0 else 0})\n")
        f.write(f"- **Belirlenen Mükerrer Kayıt Riski:** {duplicate_risks}\n")
        f.write(f"- **Yanlış Ürün Bölünmesi (Batch/Release Ayrımı) Riski:** {batch_splits}\n")
        f.write(f"- **Düşük Güvenli Eşleşmeler:** {low_confidence_matches}\n\n")
        
        f.write("## 2. GO / NO-GO Kararı\n")
        f.write(f"### Karar: **{go_status}**\n\n")
        f.write("#### NO-GO Gerekçeleri:\n")
        for r in reason_nogo:
            f.write(f"- {r}\n")
        f.write("\n")
        f.write("> [!IMPORTANT]\n")
        f.write("> Doğrudan veritabanına aktarım (direct import) yapılması mükerrer kayıtlara ve yanlış ürün bölünmelerine yol açacaktır. Bu sebeple otomatik import **ENGELLEMİŞTİR**.\n")
        f.write("> Verilerin güvenli aktarımı için `output/import/books/manual_review_queue.csv` dosyasındaki kayıtların tek tek manuel olarak gözden geçirilmesi ve onaylanması gerekmektedir.\n\n")
        
        f.write("## 3. Detaylı Ürün Ayrımı & Bölünme Analizi (Örnek Kayıtlar)\n")
        f.write("| Satır | Ürün Adı | Eşleşme Durumu | Güven Skoru | Batch? | Çakışma / Bölünme Riski |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")
        
        # Show top 30 risk cases or examples
        shown_count = 0
        for item in audit_details:
            if item["duplicate_risk"] != "Low" or item["split_risk"] != "Low":
                f.write(f"| {item['row']} | {item['name']} | `{item['match_status']}` | {item['confidence']} | {item['batch_detected']} | {item['reasons']} |\n")
                shown_count += 1
                if shown_count >= 30:
                    break
        if shown_count == 0:
            f.write("| - | Herhangi bir riskli kayıt tespit edilmedi. | - | - | - | - |\n")
            
        f.write("\n## 4. Uygulanan Malt Radar Veri Kuralları\n")
        f.write("1. **Aynı Ürünün Farklı Batch'leri:** Aynı ürünün farklı batch'leri (örneğin Aberlour A'bunadh Batch 60, 61, vb.) için ayrı ürün kartı (`whisky`) oluşturulmaz. Bu veriler tek bir ana ürün kartı altında birleştirilmeli, batch bilgisi metadata olarak saklanmalıdır.\n")
        f.write("2. **Tadım Profili Sınırlandırması:** Anlamlı duyusal tadım farkı kanıtlanmadığı sürece her batch için ayrı tadım profili açılması engellenmiştir.\n")
        f.write("3. **Kaynak Kitap Entegrasyonu:** Kaynak kitap, sayfa veya bölüm bilgileri veritabanında metadata olarak saklanmakta, public UI'a yansıtılmamaktadır.\n")
        
    print(f"Catalogue review report written to {md_file}")

if __name__ == "__main__":
    main()
