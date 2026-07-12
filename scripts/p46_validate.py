import csv
import re
import sqlite3
import difflib
from pathlib import Path

# Paths
REPO_ROOT = Path(r"C:\Users\eltun\Documents\malt radar CLEAN")
CSV_PATH = REPO_ROOT / "output" / "reports" / "p46_review_recommendations.csv"
STATS_PATH = REPO_ROOT / "output" / "reports" / "p46_statistics.md"
HIGH_RISK_PATH = REPO_ROOT / "output" / "reports" / "p46_high_risk_cases.md"
VALIDATION_OUT = REPO_ROOT / "output" / "reports" / "p46_validation.md"
DB_PATH = REPO_ROOT / "output" / "import" / "production.db"

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
    print("Reading recommendations CSV...")
    if not CSV_PATH.exists():
        print("CSV not found!")
        return
        
    rows = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
            
    total_reviewed = len(rows)
    print(f"Total reviewed in CSV: {total_reviewed}")
    
    # Count actions in CSV
    action_counts = {}
    for r in rows:
        action = r["recommended_action"]
        action_counts[action] = action_counts.get(action, 0) + 1
        
    # Connect to DB to load whiskies for verification
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    existing_whiskies = {}
    cursor.execute("SELECT whisky_id, name, abv FROM whiskies;")
    for row in cursor.fetchall():
        w_id = row[0]
        existing_whiskies[w_id] = {
            "name": row[1].strip() if row[1] else "",
            "abv": row[2]
        }
    conn.close()
    
    # Calculate probabilities using the exact same logic
    duplicate_count_prob = 0
    batch_count_prob = 0
    new_expr_count_prob = 0
    hr_csv_count = 0
    
    for r in rows:
        name = r["candidate_name"]
        matched_id = r["matched_id"] if "matched_id" in r else r.get("matched_whisky", "None")
        confidence = float(r["confidence"])
        
        db_whisky = None
        if matched_id != "None" and matched_id in existing_whiskies:
            db_whisky = existing_whiskies[matched_id]
        else:
            best_match_id = None
            best_score = 0.0
            for ex_id, ex in existing_whiskies.items():
                score = get_similarity(name, ex["name"])
                if score > best_score:
                    best_score = score
                    best_match_id = ex_id
            if best_score >= 0.60:
                db_whisky = existing_whiskies[best_match_id]
                
        duplicate_prob = 0.0
        batch_prob = 0.0
        new_prod_prob = 0.0
        
        if db_whisky:
            db_name = db_whisky["name"]
            sim = get_similarity(name, db_name)
            source_batch = detect_batch_keywords(name)
            db_batch = detect_batch_keywords(db_name)
            is_batch = len(source_batch) > 0 or len(db_batch) > 0
            
            source_age_match = re.search(r'\b(\d{1,2})\b\s*(?:years|year|yo|y\.o\.|y|old)', name.lower())
            db_age_match = re.search(r'\b(\d{1,2})\b\s*(?:years|year|yo|y\.o\.|y|old)', db_name.lower())
            source_age = int(source_age_match.group(1)) if source_age_match else None
            db_age = int(db_age_match.group(1)) if db_age_match else None
            has_age_diff = source_age and db_age and source_age != db_age
            
            cask_keywords = ["sherry", "port", "rum", "wine", "cask finish", "wood finish", "amarone", "lustau", "madera"]
            source_casks = [k for k in cask_keywords if k in name.lower()]
            db_casks = [k for k in cask_keywords if k in db_name.lower()]
            has_cask_diff = len(source_casks) != len(db_casks) or set(source_casks) != set(db_casks)
            
            has_abv_diff = False
            source_abv_match = re.search(r'\b(\d{2}(?:\.\d+)?)\s*%', name)
            db_abv = db_whisky["abv"]
            if source_abv_match and db_abv:
                source_abv = float(source_abv_match.group(1))
                if abs(source_abv - db_abv) > 0.1:
                    has_abv_diff = True
                    
            if sim >= 0.98 and not has_abv_diff and not has_age_diff:
                duplicate_prob = 0.95
            elif has_age_diff:
                new_prod_prob = 0.95
            elif source_age_match is None and db_age_match is not None:
                duplicate_prob = 0.50
                new_prod_prob = 0.50
            elif has_cask_diff:
                new_prod_prob = 0.85
            elif is_batch:
                batch_prob = 0.95
                duplicate_prob = 0.80
            elif has_abv_diff:
                duplicate_prob = 0.50
            elif sim >= 0.85:
                duplicate_prob = 0.85
            else:
                new_prod_prob = 0.75
        else:
            new_prod_prob = 0.98
            
        if duplicate_prob > 0.70: duplicate_count_prob += 1
        if batch_prob > 0.70: batch_count_prob += 1
        if new_prod_prob > 0.70: new_expr_count_prob += 1
        
        if confidence < 0.80 or duplicate_prob > 0.70:
            hr_csv_count += 1
            
    # Read statistics report
    stats_content = ""
    if STATS_PATH.exists():
        with open(STATS_PATH, "r", encoding="utf-8") as f:
            stats_content = f.read()
            
    total_stat_m = re.search(r'total reviewed\b.*?(\d+)', stats_content, re.IGNORECASE)
    keep_stat_m = re.search(r'KEEP_EXISTING\b.*?(\d+)', stats_content)
    merge_stat_m = re.search(r'MERGE_METADATA\b.*?(\d+)', stats_content)
    new_stat_m = re.search(r'CREATE_NEW_PRODUCT\b.*?(\d+)', stats_content)
    manual_stat_m = re.search(r'MANUAL_REVIEW\b.*?(\d+)', stats_content)
    reject_stat_m = re.search(r'REJECT\b.*?(\d+)', stats_content)
    
    dup_rate_m = re.search(r'duplicate rate\b.*?%?(\d+(?:\.\d+)?)', stats_content, re.IGNORECASE)
    batch_rate_m = re.search(r'batch-only rate\b.*?%?(\d+(?:\.\d+)?)', stats_content, re.IGNORECASE)
    new_expr_rate_m = re.search(r'new expression rate\b.*?%?(\d+(?:\.\d+)?)', stats_content, re.IGNORECASE)
    
    total_stat = int(total_stat_m.group(1)) if total_stat_m else 0
    keep_stat = int(keep_stat_m.group(1)) if keep_stat_m else 0
    merge_stat = int(merge_stat_m.group(1)) if merge_stat_m else 0
    new_stat = int(new_stat_m.group(1)) if new_stat_m else 0
    manual_stat = int(manual_stat_m.group(1)) if manual_stat_m else 0
    reject_stat = int(reject_stat_m.group(1)) if reject_stat_m else 0
    
    dup_rate_stat = float(dup_rate_m.group(1)) if dup_rate_m else 0.0
    batch_rate_stat = float(batch_rate_m.group(1)) if batch_rate_m else 0.0
    new_expr_rate_stat = float(new_expr_rate_m.group(1)) if new_expr_rate_m else 0.0
    
    inconsistencies = []
    
    if total_reviewed != total_stat:
        inconsistencies.append(f"Total reviewed count mismatch: CSV has {total_reviewed}, stats report has {total_stat}.")
        
    csv_keep = action_counts.get("KEEP_EXISTING", 0)
    if csv_keep != keep_stat:
        inconsistencies.append(f"KEEP_EXISTING count mismatch: CSV has {csv_keep}, stats report has {keep_stat}.")
        
    csv_merge = action_counts.get("MERGE_METADATA", 0)
    if csv_merge != merge_stat:
        inconsistencies.append(f"MERGE_METADATA count mismatch: CSV has {csv_merge}, stats report has {merge_stat}.")
        
    csv_new = action_counts.get("CREATE_NEW_PRODUCT", 0)
    if csv_new != new_stat:
        inconsistencies.append(f"CREATE_NEW_PRODUCT count mismatch: CSV has {csv_new}, stats report has {new_stat}.")
        
    csv_manual = action_counts.get("MANUAL_REVIEW", 0)
    if csv_manual != manual_stat:
        inconsistencies.append(f"MANUAL_REVIEW count mismatch: CSV has {csv_manual}, stats report has {manual_stat}.")
        
    csv_reject = action_counts.get("REJECT", 0)
    if csv_reject != reject_stat:
        inconsistencies.append(f"REJECT count mismatch: CSV has {csv_reject}, stats report has {reject_stat}.")
        
    # Check percentages
    def check_percent(value, total, label):
        expected_1d = round(value / total * 100, 1)
        expected_2d = round(value / total * 100, 2)
        match = re.search(label + r'\b.*?\(%(\d+(?:\.\d+)?)\)', stats_content)
        if match:
            pct_val = float(match.group(1))
            if pct_val != expected_1d and pct_val != expected_2d:
                inconsistencies.append(f"{label} percentage mismatch: expected {expected_2d}% or {expected_1d}%, report has {pct_val}%.")

    check_percent(csv_keep, total_reviewed, "KEEP_EXISTING")
    check_percent(csv_merge, total_reviewed, "MERGE_METADATA")
    check_percent(csv_new, total_reviewed, "CREATE_NEW_PRODUCT")
    check_percent(csv_manual, total_reviewed, "MANUAL_REVIEW")
    check_percent(csv_reject, total_reviewed, "REJECT")
    
    # Check probability rates
    expected_dup_rate = round(duplicate_count_prob / total_reviewed * 100, 2)
    expected_batch_rate = round(batch_count_prob / total_reviewed * 100, 2)
    expected_new_expr_rate = round(new_expr_count_prob / total_reviewed * 100, 2)
    
    if abs(dup_rate_stat - expected_dup_rate) > 0.05:
        inconsistencies.append(f"Duplicate rate mismatch: expected {expected_dup_rate}%, report has {dup_rate_stat}%.")
    if abs(batch_rate_stat - expected_batch_rate) > 0.05:
        inconsistencies.append(f"Batch-only rate mismatch: expected {expected_batch_rate}%, report has {batch_rate_stat}%.")
    if abs(new_expr_rate_stat - expected_new_expr_rate) > 0.05:
        inconsistencies.append(f"New expression rate mismatch: expected {expected_new_expr_rate}%, report has {new_expr_rate_stat}%.")
        
    # Verify high risk cases report count
    high_risk_content = ""
    if HIGH_RISK_PATH.exists():
        with open(HIGH_RISK_PATH, "r", encoding="utf-8") as f:
            high_risk_content = f.read()
            
    total_hr_stat_m = re.search(r'Toplam Yüksek Riskli Aday:\s*\*?\*?\s*(\d+)', high_risk_content, re.IGNORECASE)
    total_hr_stat = int(total_hr_stat_m.group(1)) if total_hr_stat_m else 0
    
    if hr_csv_count != total_hr_stat:
        inconsistencies.append(f"High risk case count mismatch: calculated {hr_csv_count}, report lists {total_hr_stat}.")

    status = "FAIL" if inconsistencies else "PASS"
    
    with open(VALIDATION_OUT, "w", encoding="utf-8") as f:
        f.write("# Malt Radar P46 - Veri Validasyon ve Doğrulama Raporu\n\n")
        f.write("**Oluşturulma Tarihi:** 2026-07-12\n")
        f.write(f"**Validasyon Durumu (Status):** **{status}**\n\n")
        
        f.write("## 1. Doğrulama Bulguları (Inconsistency Audit)\n")
        if inconsistencies:
            for inc in inconsistencies:
                f.write(f"- [ ] **UYUŞMAZLIK:** {inc}\n")
        else:
            f.write("- [x] Tüm istatistikler ve yüzdeler CSV dosyasıyla tam olarak uyuşmaktadır.\n")
            f.write("- [x] Birebir veri doğrulaması başarılıdır.\n")
            
        f.write("\n## 2. CSV Verileri ile İstatistik Raporu Karşılaştırması\n")
        f.write("| Metrik | CSV Sayımı | İstatistik Raporu Değeri | Durum |\n")
        f.write("| --- | --- | --- | --- |\n")
        f.write(f"| Toplam Kayıt | {total_reviewed} | {total_stat} | {'PASS' if total_reviewed == total_stat else 'FAIL'} |\n")
        f.write(f"| KEEP_EXISTING | {csv_keep} | {keep_stat} | {'PASS' if csv_keep == keep_stat else 'FAIL'} |\n")
        f.write(f"| MERGE_METADATA | {csv_merge} | {merge_stat} | {'PASS' if csv_merge == merge_stat else 'FAIL'} |\n")
        f.write(f"| CREATE_NEW_PRODUCT | {csv_new} | {new_stat} | {'PASS' if csv_new == new_stat else 'FAIL'} |\n")
        f.write(f"| MANUAL_REVIEW | {csv_manual} | {manual_stat} | {'PASS' if csv_manual == manual_stat else 'FAIL'} |\n")
        f.write(f"| REJECT | {csv_reject} | {reject_stat} | {'PASS' if csv_reject == reject_stat else 'FAIL'} |\n")
        
        f.write("\n## 3. Olasılık Oranları Doğrulaması (Reproducibility)\n")
        f.write(f"- **Mükerrerlik Oranı (duplicate rate):** Rapor: %{dup_rate_stat} | Yeniden Hesaplanan: %{expected_dup_rate} ({'Uyuşuyor' if abs(dup_rate_stat - expected_dup_rate) < 0.1 else 'Çelişki'})\n")
        f.write(f"- **Batch Farklılığı Oranı (batch-only rate):** Rapor: %{batch_rate_stat} | Yeniden Hesaplanan: %{expected_batch_rate} ({'Uyuşuyor' if abs(batch_rate_stat - expected_batch_rate) < 0.1 else 'Çelişki'})\n")
        f.write(f"- **Yeni İfade Oranı (new expression rate):** Rapor: %{new_expr_rate_stat} | Yeniden Hesaplanan: %{expected_new_expr_rate} ({'Uyuşuyor' if abs(new_expr_rate_stat - expected_new_expr_rate) < 0.1 else 'Çelişki'})\n")
        
        f.write("\n## 4. GO / NO-GO Tavsiyesi (GO / NO-GO Recommendation)\n")
        if status == "PASS":
            f.write("### Karar: **GO (Manuel Review Başlayabilir)**\n\n")
            f.write("Tüm istatistiksel metrikler ve veri çıktıları birbiriyle tutarlıdır. İnceleme dosyaları karar şablonuna aktarılabilir.\n")
        else:
            f.write("### Karar: **NO-GO (Hata Giderilmesi Gerekiyor)**\n\n")
            f.write("Yukarıda belirtilen uyuşmazlıklar giderilene kadar manuel inceleme aşamasına geçilmesi önerilmez.\n")
            
    print(f"Validation report written to {VALIDATION_OUT}")

if __name__ == "__main__":
    main()
