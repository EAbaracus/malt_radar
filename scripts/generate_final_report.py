import os
import csv
from pathlib import Path

# Paths
REPO_ROOT = Path(r"C:\Users\eltun\Documents\malt radar CLEAN")
STAGING_DIR = REPO_ROOT / "output" / "import" / "books"
REPORT_DIR = REPO_ROOT / "output" / "reports"

os.makedirs(REPORT_DIR, exist_ok=True)

def main():
    print("Reading review queues...")
    
    cat_queue_file = STAGING_DIR / "catalogue_review_queue.csv"
    dist_queue_file = STAGING_DIR / "distillery_review_queue.csv"
    brand_queue_file = STAGING_DIR / "brand_review_queue.csv"
    
    # ---------------- 1. CATALOGUE STATISTICS & RISK CASE LIST ----------------
    cat_records = []
    cat_stats = {
        "total": 0,
        "KEEP_EXISTING": 0,
        "MERGE_METADATA": 0,
        "CREATE_NEW_PRODUCT": 0,
        "REJECT": 0,
        "MANUAL_RESOLVE": 0 # Just in case
    }
    
    if cat_queue_file.exists():
        with open(cat_queue_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cat_records.append(row)
                action = row["recommended_action"]
                cat_stats[action] = cat_stats.get(action, 0) + 1
                cat_stats["total"] += 1
                
        # Sort by risk (High, then Medium, then Low) and lowest confidence
        def risk_score(item):
            d_risk = item["duplicate_risk"].lower()
            s_risk = item["split_risk"].lower()
            score = 0
            if "high" in d_risk: score += 10
            elif "medium" in d_risk: score += 5
            if "high" in s_risk: score += 10
            elif "medium" in s_risk: score += 5
            
            # Sub-sort by lower confidence if matched, or higher confidence if new but similar
            conf = float(item["confidence"])
            # We want fuzzy matches with lower confidence first, or new products with higher near-match potential
            return (score, -conf)
            
        sorted_cat_records = sorted(cat_records, key=risk_score, reverse=True)
        top_50_risky_cat = sorted_cat_records[:50]
    else:
        print("Warning: catalogue_review_queue.csv not found.")
        top_50_risky_cat = []
        
    # ---------------- 2. DISTILLERY STATISTICS & LISTS ----------------
    dist_records = []
    dist_merge_candidates = []
    dist_new_candidates = []
    dist_uncertain = []
    
    if dist_queue_file.exists():
        with open(dist_queue_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                dist_records.append(row)
                rec = row["recommendation"]
                c_match = row["candidate_match"]
                
                if rec in ("MERGE_METADATA", "MANUAL_RESOLVE") and c_match != "None":
                    dist_merge_candidates.append(row)
                if rec == "CREATE_NEW_DISTILLERY":
                    dist_new_candidates.append(row)
                if rec == "MANUAL_RESOLVE" or row["country_match"] == "No" or row["location_match"] == "No":
                    dist_uncertain.append(row)
    else:
        print("Warning: distillery_review_queue.csv not found.")
        
    # ---------------- 3. BRAND STATISTICS & LISTS ----------------
    brand_records = []
    brand_merge_candidates = []
    brand_new_candidates = []
    
    if brand_queue_file.exists():
        with open(brand_queue_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                brand_records.append(row)
                rec = row["recommendation"]
                c_brand = row["candidate_brand"]
                
                if rec in ("MERGE_METADATA", "MANUAL_RESOLVE") and c_brand != "None":
                    brand_merge_candidates.append(row)
                if rec == "CREATE_NEW_BRAND":
                    brand_new_candidates.append(row)
    else:
        print("Warning: brand_review_queue.csv not found.")
        
    # Write report
    report_file = REPORT_DIR / "books_final_review_package.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# Malt Radar - Yeni Veri Kitapları Final Manuel Review Paketi Raporu\n\n")
        f.write("**Oluşturulma Tarihi:** 2026-07-12\n")
        f.write("**Kaynak Dizin:** `output/import/books/`\n")
        f.write("**Amaç:** Entegrasyon öncesi karar vericinin (insan) doğrulamasını kolaylaştırmak ve veri kalitesini maksimize etmek.\n\n")
        
        # --- SECTION 1: CATALOGUE ---
        f.write("## 1. Viski Kataloğu Denetimi (Catalogue Audit)\n\n")
        f.write("### 1.1. Metrikler & Dağılım\n")
        f.write(f"- **Toplam Katalog Kaydı:** {cat_stats['total']}\n")
        f.write(f"  - `KEEP_EXISTING` (Zaten var olan ürün, aksiyon yok): {cat_stats.get('KEEP_EXISTING', 0)}\n")
        f.write(f"  - `MERGE_METADATA` (Batch/veri birleştirme, metadata zenginleştirme): {cat_stats.get('MERGE_METADATA', 0)}\n")
        f.write(f"  - `CREATE_NEW_PRODUCT` (Yeni özgün viski kaydı): {cat_stats.get('CREATE_NEW_PRODUCT', 0)}\n")
        f.write(f"  - `REJECT` (Düşük güvenli/çakışan çöp kayıtlar): {cat_stats.get('REJECT', 0)}\n\n")
        
        f.write("### 1.2. En Riskli 50 Katalog Kaydı (Mükerrer ve Bölünme Tehditleri)\n")
        f.write("Aşağıdaki kayıtlar, mevcuttaki viskilerle isim/batch benzerliği nedeniyle **yanlış split (bölünme)** veya **mükerrer kart (duplicate)** oluşturma riski taşımaktadır:\n\n")
        f.write("| Satır | Ürün Adı | Mevcut Eşleşme | Önerilen Aksiyon | Çakışma Nedeni / Risk | Güven Skoru |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")
        
        for item in top_50_risky_cat:
            f.write(f"| {item['source_row']} | {item['product_name']} | `{item['existing_match']}` | **{item['recommended_action']}** | Duplicate: {item['duplicate_risk']} / Split: {item['split_risk']} | {item['confidence']} |\n")
            
        f.write("\n--- \n\n")
        
        # --- SECTION 2: DISTILLERY ---
        f.write("## 2. Damıtımevi Denetimi (Distillery Audit)\n\n")
        f.write("### 2.1. Metrikler & Dağılım\n")
        f.write(f"- **Toplam Damıtımevi Satırı:** {len(dist_records)}\n")
        f.write(f"- **Birleştirme (Merge) Adayı Damıtımevleri:** {len(dist_merge_candidates)}\n")
        f.write(f"- **Yeni Damıtımevi Adayları:** {len(dist_new_candidates)}\n")
        f.write(f"- **Ülke/Konum Çelişen Belirsiz Kayıtlar:** {len(dist_uncertain)}\n\n")
        
        f.write("### 2.2. Birleştirme (Merge) ve Belirsiz Damıtımevi Kayıtları (Örnekler)\n")
        f.write("| Kaynak Adı | Mevcut Eşleşme Adayı | Ülke Eşleşmesi | Konum Eşleşmesi | Önerilen Aksiyon | Neden |\n")
        f.write("| --- | --- | --- | --- | --- | --- |\n")
        
        shown_dist = 0
        for item in dist_merge_candidates + dist_uncertain:
            # Avoid showing exact matches that are perfect to keep table readable
            if item["country_match"] == "No" or item["location_match"] == "No" or item["recommendation"] == "MANUAL_RESOLVE":
                f.write(f"| {item['source_name']} | {item['candidate_match']} | {item['country_match']} | {item['location_match']} | **{item['recommendation']}** | Veri çelişkisi veya fuzzy eşleşme |\n")
                shown_dist += 1
                if shown_dist >= 30:
                    break
        if shown_dist == 0:
            # show first 10 merge candidates as examples
            for item in dist_merge_candidates[:15]:
                f.write(f"| {item['source_name']} | {item['candidate_match']} | {item['country_match']} | {item['location_match']} | **{item['recommendation']}** | İsim varyasyonu birleştirmesi |\n")
        f.write("\n")
        
        f.write("### 2.3. Yeni Damıtımevi Giriş Adayları (İlk 15)\n")
        f.write("Aşağıdaki üreticiler veritabanında bulunamamıştır ve yeni damıtımevi olarak eklenecektir:\n\n")
        f.write("| Kaynak Adı | Öneri |\n")
        f.write("| --- | --- |\n")
        for item in dist_new_candidates[:15]:
            f.write(f"| {item['source_name']} | {item['recommendation']} |\n")
            
        f.write("\n--- \n\n")
        
        # --- SECTION 3: BRAND ---
        f.write("## 3. Marka Denetimi (Brand Audit)\n\n")
        f.write("### 3.1. Metrikler & Dağılım\n")
        f.write(f"- **Toplam Marka Kaydı:** {len(brand_records)}\n")
        f.write(f"- **Birleştirme (Merge) Adayı Markalar:** {len(brand_merge_candidates)}\n")
        f.write(f"- **Yeni Marka Adayları:** {len(brand_new_candidates)}\n\n")
        
        f.write("### 3.2. Marka Birleştirme Adayları (İlk 15)\n")
        f.write("Mevcut markalarla isim varyasyonu gösteren marka adayları:\n\n")
        f.write("| Kaynak Marka | Eşleşme Adayı | Sahip Uyuşması | Önerilen Aksiyon |\n")
        f.write("| --- | --- | --- | --- |\n")
        for item in brand_merge_candidates[:15]:
            f.write(f"| {item['source_brand']} | {item['candidate_brand']} | {item['owner_match']} | **{item['recommendation']}** |\n")
            
        f.write("\n### 3.3. Yeni Eklenecek Marka Adayları (İlk 15)\n")
        f.write("| Kaynak Marka | Öneri |\n")
        f.write("| --- | --- |\n")
        for item in brand_new_candidates[:15]:
            f.write(f"| {item['source_brand']} | {item['recommendation']} |\n")
            
        f.write("\n## 4. GO / NO-GO ve Aksiyon Kuralları Hatırlatması\n")
        f.write("> [!CAUTION]\n")
        f.write("> **Otomatik Import Kararı: NO-GO**\n")
        f.write("> Veritabanında mükerrer kayıt üretilmesini önlemek amacıyla doğrudan import engellenmiştir. Entegrasyon adımları sadece staging dosyalarından manuel review ile yürütülmelidir.\n\n")
        f.write("1. **Aynı Viskinin Farklı Batch'leri:** Aynı ürünün farklı batch'leri için yeni ürün kartı açılmaz. Bu kayıtlar mevcut ana ürün kartı altında birleştirilir.\n")
        f.write("2. **Duyusal Profiller:** Her yeni batch için ek tadım profili oluşturulması engellenmiştir.\n")
        f.write("3. **Kaynak İzlenebilirliği:** Kaynak kitap bilgileri veritabanında sadece dahili metadata olarak tutulmalıdır.\n")
        
    print(f"Final review package report written to {report_file}")

if __name__ == "__main__":
    main()
